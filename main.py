#!/usr/bin/env python3
import asyncio
import json
import os
import random
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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

# Config (defaults act as fallback if token file missing)
CLIENT_ID = "zU4XHVVkc2tDPo4t"
CLIENT_SECRET = "VJKhDFqJPqvsPVNBV6ukXTJmwlvbttP7wlMlrc72se4="
REFRESH_TOKEN: Optional[str] = None
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
                # Access tokens in file have unknown expiry; force refresh on first use
                "access_token": None,
                "expires_at": 0,
            }
            if cred["refresh_token"]:
                _creds.append(cred)

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
        return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Resource not found")
        raise HTTPException(status_code=e.response.status_code, detail="Upstream API error")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Connection error to Tidal")

@app.get("/")
async def index():
    return {"HIFI-API": "v2.0", "Repo": "https://github.com/uimaxbai/hifi-api"}

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

@app.get("/search/")
async def search(q: str, type: str = "TRACKS", limit: int = 25):
    url = "https://api.tidal.com/v1/search"
    params = {
        "query": q,
        "limit": limit,
        "offset": 0,
        "types": type,
        "countryCode": "US",
    }
    return await make_request(url, params=params)

@app.get("/album/{id}")
async def get_album(id: int):
    url = f"https://api.tidal.com/v1/albums/{id}/items"
    return await make_request(url, params={"limit": 100, "countryCode": "US"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)