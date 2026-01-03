#!/usr/bin/env python3
import asyncio
import json
import os
import random
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Union

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# Shared HTTP client is created in app lifespan for connection reuse
_http_client: Optional[httpx.AsyncClient] = None

# One lock per credential to avoid global contention during token refreshes
_refresh_locks: Dict[str, asyncio.Lock] = {}

# Loaded credential set from token.json; each entry will be enriched with access cache
_creds: List[dict] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client
    _http_client = httpx.AsyncClient(
        http2=True,
        timeout=httpx.Timeout(connect=3.0, read=12.0, write=8.0, pool=12.0),
        limits=httpx.Limits(
            max_keepalive_connections=200,
            max_connections=300,
            keepalive_expiry=30.0,
        ),
    )
    try:
        yield
    finally:
        if _http_client:
            await _http_client.aclose()


app = FastAPI(
    title="HiFi-RestAPI",
    version="2.0",
    description="Tidal Music Proxy",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_VERSION = "2.1"

# Config (defaults act as fallback if token file missing)
CLIENT_ID = os.getenv("CLIENT_ID", "zU4XHVVkc2tDPo4t")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "VJKhDFqJPqvsPVNBV6ukXTJmwlvbttP7wlMlrc72se4=")
REFRESH_TOKEN: Optional[str] = os.getenv("REFRESH_TOKEN")
USER_ID = os.getenv("USER_ID")
TOKEN_FILE = os.getenv("TOKEN_FILE", "token.json")

if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, "r") as tok:
        token_data = json.load(tok)
        if isinstance(token_data, dict):
            token_data = [token_data]

        for entry in token_data:
            cred = {
                "client_id": entry.get("client_ID") or CLIENT_ID,
                "client_secret": entry.get("client_secret") or CLIENT_SECRET,
                "refresh_token": entry.get("refresh_token") or REFRESH_TOKEN,
                "user_id": entry.get("userID") or USER_ID,
                # Access tokens in file have unknown expiry; force refresh on first use
                "access_token": None,
                "expires_at": 0,
            }
            if cred["refresh_token"]:
                _creds.append(cred)

# Add env var credential if available and unique (simple check)
if REFRESH_TOKEN:
    env_cred = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "user_id": USER_ID,
        "access_token": None,
        "expires_at": 0,
    }
    # Avoid adding duplicate if it was already loaded from file with same refresh token
    if not any(c["refresh_token"] == REFRESH_TOKEN for c in _creds):
        _creds.append(env_cred)

if _creds:
    CLIENT_ID = _creds[0]["client_id"]
    CLIENT_SECRET = _creds[0]["client_secret"]
    REFRESH_TOKEN = _creds[0]["refresh_token"]


def _pick_credential() -> dict:
    if not _creds:
        raise HTTPException(status_code=500, detail="No Tidal credentials available; populate token.json")
    return random.choice(_creds)


def _lock_for_cred(cred: dict) -> asyncio.Lock:
    key = f"{cred['client_id']}:{cred['refresh_token']}"
    lock = _refresh_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _refresh_locks[key] = lock
    return lock


async def get_http_client() -> httpx.AsyncClient:
    if _http_client is None:
        # Fallback for contexts where lifespan is not run (e.g., direct calls)
        return httpx.AsyncClient(http2=True)
    return _http_client


async def refresh_tidal_token(cred: Optional[dict] = None):
    """Refresh a token for the provided credential set."""
    cred = cred or _pick_credential()

    async with _lock_for_cred(cred):
        if cred["access_token"] and time.time() < cred["expires_at"]:
            return cred["access_token"]

        try:
            client = await get_http_client()
            res = await client.post(
                "https://auth.tidal.com/v1/oauth2/token",
                data={
                    "client_id": cred["client_id"],
                    "refresh_token": cred["refresh_token"],
                    "grant_type": "refresh_token",
                    "scope": "r_usr+w_usr+w_sub",
                },
                auth=(cred["client_id"], cred["client_secret"]),
            )
            res.raise_for_status()
            data = res.json()
            new_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)

            cred["access_token"] = new_token
            cred["expires_at"] = time.time() + expires_in - 60

            return new_token
        except httpx.HTTPError as e:
            raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")


async def get_tidal_token(force_refresh: bool = False):
    return await get_tidal_token_for_cred(force_refresh=force_refresh)


async def get_tidal_token_for_cred(force_refresh: bool = False, cred: Optional[dict] = None):
    """Retrieve an access token for a specific credential; pick random if not provided."""
    cred = cred or _pick_credential()

    if not force_refresh and cred["access_token"] and time.time() < cred["expires_at"]:
        return cred["access_token"], cred

    token = await refresh_tidal_token(cred)
    return token, cred


async def make_request(url: str, token: Optional[str] = None, params: Optional[dict] = None, cred: Optional[dict] = None):
    if token is None:
        token, cred = await get_tidal_token_for_cred(cred=cred)
    client = await get_http_client()
    headers = {"authorization": f"Bearer {token}"}

    try:
        resp = await client.get(url, headers=headers, params=params)

        if resp.status_code == 401:
            # Token expired, refresh and retry
            token, cred = await get_tidal_token_for_cred(force_refresh=True, cred=cred)
            headers = {"authorization": f"Bearer {token}"}
            resp = await client.get(url, headers=headers, params=params)

        resp.raise_for_status()
        return {"version": API_VERSION, "data": resp.json()}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Resource not found")
        raise HTTPException(status_code=e.response.status_code, detail="Upstream API error")
    except httpx.RequestError as e:
        if isinstance(e, httpx.TimeoutException):
            raise HTTPException(status_code=429, detail="Upstream timeout")
        raise HTTPException(status_code=503, detail="Connection error to Tidal")


async def authed_get_json(
    url: str,
    *,
    params: Optional[dict] = None,
    token: Optional[str] = None,
    cred: Optional[dict] = None,
):
    """Perform an authenticated GET, retrying once on 401. Returns payload with updated token/cred."""

    if token is None:
        token, cred = await get_tidal_token_for_cred(cred=cred)

    client = await get_http_client()
    headers = {"authorization": f"Bearer {token}"}

    try:
        resp = await client.get(url, headers=headers, params=params)

        if resp.status_code == 401:
            token, cred = await get_tidal_token_for_cred(force_refresh=True, cred=cred)
            headers["authorization"] = f"Bearer {token}"
            resp = await client.get(url, headers=headers, params=params)

        resp.raise_for_status()
        return resp.json(), token, cred
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Resource not found")
        if e.response.status_code == 429:
            raise HTTPException(status_code=429, detail="Upstream rate limited")
        raise HTTPException(status_code=e.response.status_code, detail="Upstream API error")
    except httpx.RequestError as e:
        if isinstance(e, httpx.TimeoutException):
            raise HTTPException(status_code=429, detail="Upstream timeout")
        raise HTTPException(status_code=503, detail="Connection error to Tidal")

@app.get("/")
async def index():
    return {"version": API_VERSION, "Repo": "https://github.com/uimaxbai/hifi-api"}

@app.get("/info/")
async def get_info(id: int):
    url = f"https://api.tidal.com/v1/tracks/{id}/"
    return await make_request(url, params={"countryCode": "US"})

@app.get("/track/")
async def get_track(id: int, quality: str = "HI_RES_LOSSLESS"):
    track_url = f"https://tidal.com/v1/tracks/{id}/playbackinfo"
    params = {
        "audioquality": quality,
        "playbackmode": "STREAM",
        "assetpresentation": "FULL",
    }
    return await make_request(track_url, params=params)

@app.api_route("/search/", methods=["GET"])
async def search(
    s: Union[str, None] = Query(default=None),
    a: Union[str, None] = Query(default=None),
    al: Union[str, None] = Query(default=None),
    v: Union[str, None] = Query(default=None),
    p: Union[str, None] = Query(default=None),
):
    """Search endpoint supporting track/artist/album/video/playlist queries via distinct params."""
    queries = (
        (s, "https://api.tidal.com/v1/search/tracks", {
            "query": s,
            "limit": 25,
            "offset": 0,
            "countryCode": "US",
        }),
        (a, "https://api.tidal.com/v1/search/top-hits", {
            "query": a,
            "limit": 25,
            "offset": 0,
            "types": "ARTISTS,TRACKS",
            "countryCode": "US",
        }),
        (al, "https://api.tidal.com/v1/search/top-hits", {
            "query": al,
            "limit": 25,
            "offset": 0,
            "types": "ALBUMS",
            "countryCode": "US",
        }),
        (v, "https://api.tidal.com/v1/search/top-hits", {
            "query": v,
            "limit": 25,
            "offset": 0,
            "types": "VIDEOS",
            "countryCode": "US",
        }),
        (p, "https://api.tidal.com/v1/search/top-hits", {
            "query": p,
            "limit": 25,
            "offset": 0,
            "types": "PLAYLISTS",
            "countryCode": "US",
        }),
    )

    for value, url, params in queries:
        if value:
            return await make_request(url, params=params)

    raise HTTPException(status_code=400, detail="Provide one of s, a, al, v, or p")

@app.get("/album/")
async def get_album(
    id: int = Query(..., description="Album ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    token, cred = await get_tidal_token_for_cred()

    album_url = f"https://api.tidal.com/v1/albums/{id}"
    items_url = f"https://api.tidal.com/v1/albums/{id}/items"

    async def fetch(url: str, params: Optional[dict] = None):
        nonlocal token, cred
        payload, token, cred = await authed_get_json(
            url,
            params=params,
            token=token,
            cred=cred,
        )
        return payload

    album_data, items_data = await asyncio.gather(
        fetch(album_url, {"countryCode": "US"}),
        fetch(items_url, {"countryCode": "US", "limit": limit, "offset": offset}),
    )

    album_data["items"] = items_data.get("items", items_data)

    return {
        "version": API_VERSION,
        "data": album_data,
    }


@app.get("/mix/")
async def get_mix(
    id: str = Query(..., description="Mix ID"),
    country_code: str = Query("US", description="Country Code"),
):
    """Fetch items from a Tidal mix by its ID."""
    token, cred = await get_tidal_token_for_cred()
    url = f"https://api.tidal.com/v1/mixes/{id}/items"
    data, _, _ = await authed_get_json(
        url,
        params={"countryCode": country_code},
        token=token,
        cred=cred,
    )
    return {"version": API_VERSION, "items": data.get("items", [])}


@app.get("/playlist/")
async def get_playlist(
    id: str = Query(..., min_length=1),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Fetch playlist metadata plus items concurrently, using shared client and single token."""

    token, cred = await get_tidal_token_for_cred()

    playlist_url = f"https://api.tidal.com/v1/playlists/{id}"
    items_url = f"https://api.tidal.com/v1/playlists/{id}/items"

    async def fetch(url: str, params: Optional[dict] = None):
        nonlocal token, cred
        payload, token, cred = await authed_get_json(
            url,
            params=params,
            token=token,
            cred=cred,
        )
        return payload

    playlist_data, items_data = await asyncio.gather(
        fetch(playlist_url, {"countryCode": "US"}),
        fetch(items_url, {"countryCode": "US", "limit": limit, "offset": offset}),
    )

    return {
        "version": API_VERSION,
        "playlist": playlist_data,
        "items": items_data.get("items", items_data),
    }


@app.get("/artist/similar/")
async def get_similar_artists(
    id: int = Query(..., description="Artist ID"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Fetch artists similar to another by its ID."""
    token, cred = await get_tidal_token_for_cred()
    
    url = f"https://api.tidal.com/v1/artists/{id}/similar"
    params = {
        "limit": limit,
        "offset": offset,
        "countryCode": "US"
    }
    
    data, _, _ = await authed_get_json(url, params=params, token=token, cred=cred)
    return {"version": API_VERSION, "artists": data.get("items", [])}


@app.get("/album/similar/")
async def get_similar_albums(
    id: int = Query(..., description="Album ID"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Fetch albums similar to another by its ID."""
    token, cred = await get_tidal_token_for_cred()
    
    url = f"https://api.tidal.com/v1/albums/{id}/similar"
    params = {
        "limit": limit,
        "offset": offset,
        "countryCode": "US"
    }
    
    data, _, _ = await authed_get_json(url, params=params, token=token, cred=cred)
    return {"version": API_VERSION, "albums": data.get("items", [])}


@app.get("/artist/")
async def get_artist(
    id: Optional[int] = Query(default=None),
    f: Optional[int] = Query(default=None),
):
    """Artist detail or album+track aggregation.

    - id: basic artist metadata + cover URLs
    - f: fetch artist albums page and aggregate tracks across albums (capped concurrency)
    """

    if id is None and f is None:
        raise HTTPException(status_code=400, detail="Provide id or f query param")

    token, cred = await get_tidal_token_for_cred()

    if id is not None:
        artist_url = f"https://api.tidal.com/v1/artists/{id}"
        artist_data, token, cred = await authed_get_json(
            artist_url,
            params={"countryCode": "US"},
            token=token,
            cred=cred,
        )

        picture = artist_data.get("picture")
        cover = None
        if picture:
            slug = picture.replace("-", "/")
            cover = {
                "id": artist_data.get("id"),
                "name": artist_data.get("name"),
                "750": f"https://resources.tidal.com/images/{slug}/750x750.jpg",
            }

        return {"version": API_VERSION, "artist": artist_data, "cover": cover}

    # Fetch albums and singles/EPs directly in parallel
    albums_url = f"https://api.tidal.com/v1/artists/{f}/albums"
    common_params = {"countryCode": "US", "limit": 100}

    results = await asyncio.gather(
        authed_get_json(albums_url, params=common_params, token=token, cred=cred),
        authed_get_json(albums_url, params={**common_params, "filter": "EPSANDSINGLES"}, token=token, cred=cred),
        return_exceptions=True
    )

    unique_releases = []
    seen_ids = set()
    for res in results:
        if isinstance(res, tuple) and len(res) > 0:
            data, token, cred = res # Update tokens from latest responses
            for item in data.get("items", []):
                if item.get("id") and item["id"] not in seen_ids:
                    unique_releases.append(item)
                    seen_ids.add(item["id"])
        elif isinstance(res, Exception):
            print(f"Error fetching artist releases: {res}")

    album_ids: List[int] = [item["id"] for item in unique_releases]
    page_data = {"items": unique_releases}

    if not album_ids:
        return {"version": API_VERSION, "albums": page_data, "tracks": []}

    sem = asyncio.Semaphore(6)

    async def fetch_album_tracks(album_id: int):
        nonlocal token, cred
        async with sem:
            album_data, token, cred = await authed_get_json(
                "https://api.tidal.com/v1/pages/album",
                params={
                    "albumId": album_id,
                    "countryCode": "US",
                    "deviceType": "BROWSER",
                },
                token=token,
                cred=cred,
            )

            rows = album_data.get("rows", [])
            if len(rows) < 2:
                return []
            modules = rows[1].get("modules", [])
            if not modules:
                return []
            paged_list = modules[0].get("pagedList", {})
            items = paged_list.get("items", [])
            tracks = [track.get("item", track) for track in items]
            return tracks

    results = await asyncio.gather(
        *(fetch_album_tracks(album_id) for album_id in album_ids),
        return_exceptions=True,
    )

    tracks: List[dict] = []
    for res in results:
        if isinstance(res, Exception):
            continue
        tracks.extend(res)

    return {"version": API_VERSION, "albums": page_data, "tracks": tracks}


@app.get("/cover/")
async def get_cover(
    id: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None),
):
    """Fetch album cover data for a track id or search query."""

    if id is None and q is None:
        raise HTTPException(status_code=400, detail="Provide id or q query param")

    token, cred = await get_tidal_token_for_cred()

    def build_cover_entry(cover_slug: str, name: Optional[str], track_id: Optional[int]):
        slug = cover_slug.replace("-", "/")
        return {
            "id": track_id,
            "name": name,
            "1280": f"https://resources.tidal.com/images/{slug}/1280x1280.jpg",
            "640": f"https://resources.tidal.com/images/{slug}/640x640.jpg",
            "80": f"https://resources.tidal.com/images/{slug}/80x80.jpg",
        }

    if id is not None:
        track_data, token, cred = await authed_get_json(
            f"https://api.tidal.com/v1/tracks/{id}/",
            params={"countryCode": "US"},
            token=token,
            cred=cred,
        )

        album = track_data.get("album") or {}
        cover_slug = album.get("cover")
        if not cover_slug:
            raise HTTPException(status_code=404, detail="Cover not found")

        entry = build_cover_entry(
            cover_slug,
            album.get("title") or track_data.get("title"),
            album.get("id") or id,
        )
        return {"version": API_VERSION, "covers": [entry]}

    search_data, token, cred = await authed_get_json(
        "https://api.tidal.com/v1/search/tracks",
        params={"countryCode": "US", "query": q, "limit": 10},
        token=token,
        cred=cred,
    )

    items = search_data.get("items", [])[:10]
    if not items:
        raise HTTPException(status_code=404, detail="Cover not found")

    covers = []
    for track in items:
        album = track.get("album") or {}
        cover_slug = album.get("cover")
        if not cover_slug:
            continue
        covers.append(
            build_cover_entry(
                cover_slug,
                track.get("title"),
                track.get("id"),
            )
        )

    if not covers:
        raise HTTPException(status_code=404, detail="Cover not found")

    return {"version": API_VERSION, "covers": covers}


@app.get("/lyrics/")
async def get_lyrics(id: int):
    url = f"https://api.tidal.com/v1/tracks/{id}/lyrics"
    data, token, cred = await authed_get_json(
        url,
        params={"countryCode": "US", "locale": "en_US", "deviceType": "BROWSER"},
    )

    if not data:
        raise HTTPException(status_code=404, detail="Lyrics not found")

    return {"version": API_VERSION, "lyrics": data}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)