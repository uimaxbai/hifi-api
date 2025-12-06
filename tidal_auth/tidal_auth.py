import asyncio
import json
import os
import random
import webbrowser
from pathlib import Path

import httpx
import rich

TOKEN_FILE = Path(os.getenv("TOKEN_FILE", Path(__file__).resolve().parent.parent / "token.json"))


class Hifi:
    def __init__(self, client_id, scope, url, client_secret):
        self.client_id = client_id
        self.scope = scope
        self.url = url
        self.client_secret = client_secret

    @staticmethod
    def Quality(quality):
        rate = {quality: "HI_RES"}
        return rate[quality]


class Auth(Hifi):
    def __init__(self, client_id, scope, url, client_secret):
        super().__init__(client_id, scope, url, client_secret)
        self.response = None

    async def get_auth_response(self):
        data = {"client_id": self.client_id, "scope": self.scope}
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G965F Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.109 Mobile Safari/537.36"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, data=data, headers=headers)
            # We handle status codes in the main loop now

        self.response = response

    def __str__(self):
        return str(self.response)


def load_tokens():
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return [data]
    return []


def save_token_entry(entry):
    tokens = load_tokens()
    tokens = [t for t in tokens if not (
        t.get("client_ID") == entry["client_ID"] and t.get("refresh_token") == entry["refresh_token"]
    )]
    tokens.append(entry)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=4)


async def poll_for_authorization(url, data, auth):
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.post(url, data=data, auth=auth)
            if response.status_code == 200:
                return response.json()
            await asyncio.sleep(5)


async def fetch_credentials():
    url = "https://api.github.com/gists/48d01f5a24b4b7b37f19443977c22cd6"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        gist_data = resp.json()
        
        content_str = gist_data["files"]["tidal-api-key.json"]["content"]
        keys_data = json.loads(content_str)
        
        hifi_creds = [
            ("fX2JxdmntZWK0ixT", "1Nn9AfDAjxrgJFJbKNWLeAyKGVGmINuXPPLHVXAvxAg=")
        ]
        other_creds = []
        
        for key_entry in keys_data["keys"]:
            if key_entry.get("valid") == "True":
                cred = (key_entry["clientId"], key_entry["clientSecret"])
                if "hifi" in key_entry.get("formats", "").lower():
                    hifi_creds.append(cred)
                else:
                    other_creds.append(cred)
        
        if not hifi_creds and not other_creds:
            raise Exception("No valid Tidal credentials found in Gist")
        return hifi_creds, other_creds


async def main():
    hifi_creds, other_creds = await fetch_credentials()
    random.shuffle(hifi_creds)
    random.shuffle(other_creds)
    all_creds = hifi_creds + other_creds

    async def run_link_flow():
        authrize = None
        for client_id, client_secret in all_creds:
            rich.print(f"Trying Client ID: {client_id}")
            authrize = Auth(
                client_id=client_id,
                scope="r_usr+w_usr+w_sub",
                url="https://auth.tidal.com/v1/oauth2/device_authorization",
                client_secret=client_secret,
            )

            try:
                await authrize.get_auth_response()
                if authrize.response.status_code == 200:
                    break
                elif authrize.response.status_code == 401:
                    rich.print(f"[yellow]Client ID {client_id} failed with 401. Trying next...[/yellow]")
                    continue
                else:
                    rich.print(f"[red]Error {authrize.response.status_code}. Trying next...[/red]")
                    continue
            except Exception as e:
                rich.print(f"[red]Exception: {e}. Trying next...[/red]")
                continue
        else:
            rich.print("[red]All tokens failed.[/red]")
            return False

        res = authrize.response.json()

        verifyurl = res["verificationUriComplete"]
        dcode = res["deviceCode"]

        rich.print(verifyurl)
        rich.print(dcode)

        HI_RES = authrize.Quality(quality="True")
        rich.print(HI_RES)

        webbrowser.open(verifyurl)

        url2 = "https://auth.tidal.com/v1/oauth2/token"

        data2 = {
            "client_id": authrize.client_id,
            "scope": authrize.scope,
            "device_code": dcode,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }

        basic = (authrize.client_id, authrize.client_secret)

        auth_response = await poll_for_authorization(url2, data2, basic)

        access_token = auth_response["access_token"]
        refresh_token = auth_response["refresh_token"]
        user_id = auth_response["user"]["userId"]
        accs = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "userID": user_id,
            "client_ID": client_id,
            "client_secret": client_secret,
        }
        save_token_entry(accs)
        rich.print(accs)
        acs_tok = access_token

        url3 = f"https://api.tidal.com/v1/tracks/286266926/playbackinfopostpaywall?countryCode=en_US&audioquality={HI_RES}&playbackmode=STREAM&assetpresentation=FULL"

        headers = {"authorization": f"Bearer {acs_tok}"}

        async with httpx.AsyncClient() as client:
            res3 = await client.get(url3, headers=headers)

        rich.print(res3.json())
        print("TOKEN IS VALID")
        return True

    while True:
        success = await run_link_flow()
        if not success:
            break
        again = input("Add another token? (y/N): ").strip().lower()
        if again not in ("y", "yes"):
            break


if __name__ == "__main__":
    asyncio.run(main())
