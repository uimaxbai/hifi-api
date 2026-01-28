# hifi-api

![Running on BiniLossless.](https://sachinsenal0x64.github.io/picx-images-hosting/hifi.5fkz01pkwn.webp)

<p align="center">Running on <a href="https://music.binimum.org/">BiniLossless</a>.</p>

`hifi-api` is forked from the original [here](https://github.com/sachinsenal0x64/hifi).

> [!IMPORTANT]
>
> This documentation is a **work-in-progress**. It is not complete however there is still lots of useful information here.

## Setup

Run `pip install -r requirements.txt` in `tidal_auth/`. Then run `tidal_auth/tidal_auth.py` and follow the instructions to authenticate. The script saves its output in a file `token.json`. Keep it safe.

> [!NOTE]
> 
> `tidal_auth.py` uses a `token.json` file. It is saved to the directory where you *ran* the script, not where the script is located.
>
> Likewise, the API expects `token.json` to be in the directory where you *run* the script, not where the script is located. Most of the time this shouldn't matter.

> [!IMPORTANT]
>
> When running `tidal_auth.py` with an existing `token.json` file, the new token is **appended** to the original `token.json`. The API randomly selects one of the tokens from the list to be used - this is intended behaviour.
>
> However, this also means that **expired tokens will not be overwritten by re-running the `tidal_auth.py` script**. If in doubt, just delete `token.json` and re-run the script.

Install dependencies for the main API with `pip install -r requirements.txt` in the main project folder.

Run the project with `python3 main.py`. It opens a web server on `0.0.0.0:8000` by default. (caution!)

> [!NOTE]
>
> Although the project may seem like it supports `.env`, it currently **does not support `.env` files or set environment variables**.

## API Schema

Scroll down a bit for information of typical flows (for example - APIs called when playing a song).

### `GET /info/`

#### Params

- `id`: `int` (required) - the Tidal ID of the track.

#### Response

`200 OK`

```json
{
    "version": "2.0",
    "data": {
        "id": 48717877,
        "title": "Waiting For Love",
        "duration": 273,
        "replayGain": -12.41,
        "peak": 0.999969,
        "allowStreaming": true,
        "streamReady": true,
        "payToStream": false,
        "adSupportedStreamReady": true,
        "djReady": true,
        "stemReady": false,
        "streamStartDate": "2015-07-10T00:00:00.000+0000",
        "premiumStreamingOnly": false,
        "trackNumber": 6,
        "volumeNumber": 1,
        "version": "Marshmello Remix",
        "popularity": 51,
        "copyright": "℗ 2015 Avicii Music AB",
        "bpm": 142,
        "key": "E",
        "keyScale": "MAJOR",
        "url": "http://www.tidal.com/track/48717877",
        "isrc": "CHB701400185",
        "editable": false,
        "explicit": false,
        "audioQuality": "LOSSLESS",
        "audioModes": [
            "STEREO"
        ],
        "mediaMetadata": {
            "tags": [
                "LOSSLESS"
            ]
        },
        "upload": false,
        "accessType": "PUBLIC",
        "spotlighted": false,
        "artist": {
            "id": 3637201,
            "name": "Avicii",
            "handle": null,
            "type": "MAIN",
            "picture": "c40836c8-3266-4b00-8274-a2ecb6ccd4ad"
        },
        "artists": [
            {
                "id": 3637201,
                "name": "Avicii",
                "handle": null,
                "type": "MAIN",
                "picture": "c40836c8-3266-4b00-8274-a2ecb6ccd4ad"
            }
        ],
        "album": {
            "id": 48717868,
            "title": "Waiting For Love (Remixes)",
            "cover": "870a9a38-cd1e-4644-93fd-044aa3be4142",
            "vibrantColor": "#f3ab4a",
            "videoCover": null
        },
        "mixes": {
            "TRACK_MIX": "00190c526a5b574ea83f372447ba67"
        }
    }
}
```

> [!NOTE]
>
> See [Track Flows/Playing a song](#) for how to handle this response, including how to display song names properly.

### `GET /track/`

#### Params

- `id`: `int` (required) - the Tidal ID of the track.
- `quality`: `str` (optional, defaults to `HI_RES_LOSSLESS`) - the quality that the track should be presented in. (`HI_RES_LOSSLESS` - up to 24-bit/192kHz FLAC, `LOSSLESS` - 16-bit/44.1kHz FLAC, `HIGH` - 320kbps AAC, `LOW` - 96kbps AAC)

#### Response

`200 OK`

##### CD Lossless/AAC

```json
{
    "version": "2.0",
    "data": {
        "trackId": 48717877,
        "assetPresentation": "FULL",
        "audioMode": "STEREO",
        "audioQuality": "LOSSLESS",
        "manifestMimeType": "application/vnd.tidal.bts",
        "manifestHash": "/smSLXXzSAVB+EsSVgyRzxtDuDo9rxPAH7n4tDwuXU4=",
        "manifest": "eyJtaW1lVHlwZSI6ImF1ZGlvL2ZsYWMiLCJjb2RlY3MiOiJmbGFjIiwiZW5jcnlwdGlvblR5cGUiOiJOT05FIiwidXJscyI6WyJodHRwczovL2xnZi5hdWRpby50aWRhbC5jb20vbWVkaWF0cmFja3MvQ0FFYUt3Z0RFaWRtWWpSaVpUQmlOalUzWWpRNE4yUTVNREJsWkdKaE56bGhPR0ppT1dNME1WODJNUzV0Y0RRLzAuZmxhYz90b2tlbj0xNzY2ODcwMDU3fk5UVmlNamhtWWpkak9UTmlOV1U0TVRNM1l6SXdOVGN4TTJRM05qVmhOakptWTJFeU5EWXdNZz09Il19",
        "albumReplayGain": -12.41,
        "albumPeakAmplitude": 0.999969,
        "trackReplayGain": -11.07,
        "trackPeakAmplitude": 0.999969,
        "bitDepth": 16,
        "sampleRate": 44100
    }
}
```

Where `manifest` is either base64 encoded JSON (use `"manifestMimeType": "application/vnd.tidal.bts"` to identify).

###### Decoded Manifest (formatted)

```json
{
  "mimeType": "audio/flac",
  "codecs": "flac",
  "encryptionType": "NONE",
  "urls": [
    "https://lgf.audio.tidal.com/mediatracks/CAEaKwgDEidmYjRiZTBiNjU3YjQ4N2Q5MDBlZGJhNzlhOGJiOWM0MV82MS5tcDQ/0.flac?token=1766870057~NTViMjhmYjdjOTNiNWU4MTM3YzIwNTcxM2Q3NjVhNjJmY2EyNDYwMg=="
  ]
}
```

##### CD Lossless/Hi-Res Lossless

```json
{
    "version": "2.0",
    "data": {
        "trackId": 194567102,
        "assetPresentation": "FULL",
        "audioMode": "STEREO",
        "audioQuality": "HI_RES_LOSSLESS",
        "manifestMimeType": "application/dash+xml",
        "manifestHash": "yyQEQ8ZX8ITLjQfFu0ADBdh/y03PpUd0NEPBz7RcuHk=",
        "manifest": "PD94bWwgdmVyc2lvbj0nMS4wJyBlbmNvZGluZz0nVVRGLTgnPz48TVBEIHhtbG5zPSJ1cm46bXBlZzpkYXNoOnNjaGVtYTptcGQ6MjAxMSIgeG1sbnM6eHNpPSJodHRwOi8vd3d3LnczLm9yZy8yMDAxL1hNTFNjaGVtYS1pbnN0YW5jZSIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHhtbG5zOmNlbmM9InVybjptcGVnOmNlbmM6MjAxMyIgeHNpOnNjaGVtYUxvY2F0aW9uPSJ1cm46bXBlZzpkYXNoOnNjaGVtYTptcGQ6MjAxMSBEQVNILU1QRC54c2QiIHByb2ZpbGVzPSJ1cm46bXBlZzpkYXNoOnByb2ZpbGU6aXNvZmYtbWFpbjoyMDExIiB0eXBlPSJzdGF0aWMiIG1pbkJ1ZmZlclRpbWU9IlBUMy45OTNTIiBtZWRpYVByZXNlbnRhdGlvbkR1cmF0aW9uPSJQVDJNNDIuODc5UyI+PFBlcmlvZCBpZD0iMCI+PEFkYXB0YXRpb25TZXQgaWQ9IjAiIGNvbnRlbnRUeXBlPSJhdWRpbyIgbWltZVR5cGU9ImF1ZGlvL21wNCIgc2VnbWVudEFsaWdubWVudD0idHJ1ZSI+PFJlcHJlc2VudGF0aW9uIGlkPSIwIiBjb2RlY3M9ImZsYWMiIGJhbmR3aWR0aD0iMTY2NzU1MyIgYXVkaW9TYW1wbGluZ1JhdGU9IjQ0MTAwIj48U2VnbWVudFRlbXBsYXRlIHRpbWVzY2FsZT0iNDQxMDAiIGluaXRpYWxpemF0aW9uPSJodHRwczovL3NwLWFkLWNmLmF1ZGlvLnRpZGFsLmNvbS9tZWRpYXRyYWNrcy9HaXNJQXhJbk9XWTBNVGs1WXpVMFpESmpaRGhqTm1RM1ptWXdOV0ZsTVdVNVpqTXpOR1ZmTmpJdWJYQTBJaUFkQUFDQVFDQUNLaENoT1h0R0VnMjNPV3duT3lra0lRRG1NZ1VOQUFDZ1FRLzAubXA0P1BvbGljeT1leUpUZEdGMFpXMWxiblFpT2lCYmV5SlNaWE52ZFhKalpTSTZJbWgwZEhCek9pOHZjM0F0WVdRdFkyWXVZWFZrYVc4dWRHbGtZV3d1WTI5dEwyMWxaR2xoZEhKaFkydHpMMGRwYzBsQmVFbHVUMWRaTUUxVWF6VlplbFV3V2tSS2FscEVhR3BPYlZFeldtMVpkMDVYUm14TlYxVTFXbXBOZWs1SFZtWk9ha2wxWWxoQk1FbHBRV1JCUVVOQlVVTkJRMHRvUTJoUFdIUkhSV2N5TTA5WGQyNVBlV3RyU1ZGRWJVMW5WVTVCUVVOblVWRXZLaUlzSWtOdmJtUnBkR2x2YmlJNmV5SkVZWFJsVEdWemMxUm9ZVzRpT25zaVFWZFRPa1Z3YjJOb1ZHbHRaU0k2TVRjMk5qZzNNRFEzTW4xOWZWMTkmYW1wO1NpZ25hdHVyZT12WH51cFNqWEJVVVRKMmdTMGRoTnVrY1ozLUNIaFNNd2ozUzIzWXVzNGpaMEV3QlNiZEJXT2xmeW5yWmxOYnQ2V0t0QjA4OGppZzM5d1YteHpERUx5RHlnTk4zb2E4Zk01cDVVaFQ3T0JKUWc2Q35pSzlEZ3FleE9ka3ZzeEpMbVlOUFdSYzJ2Qkt+TGRPbG1qNVVybEdmbGhYUHRZTn42d2g0aWQ3MHlQcllyVkNHdFZJT1ZzZlAyanpHRDFNM1EyVTkxMGNuOWdPYU15aU9YSUtncDl4MXhFajhEZW9QVDZPY3hiNC1HfmtBUzBhTDlJSFlNdn42RjMzWnU1Si1KdTFIQmN3MmNHV1IwVWZiNHM0ZUpEaE1kdWxHT1hLRmROVVlkdHVqZGdpcXBiSWlXajVWaUNieHJZa1JQVEZ0OXdncS1yMnVRWE1wOGFIZzd2MFZOV1FfXyZhbXA7S2V5LVBhaXItSWQ9SzE0TFpDWjlRVUk0SkwiIG1lZGlhPSJodHRwczovL3NwLWFkLWNmLmF1ZGlvLnRpZGFsLmNvbS9tZWRpYXRyYWNrcy9HaXNJQXhJbk9XWTBNVGs1WXpVMFpESmpaRGhqTm1RM1ptWXdOV0ZsTVdVNVpqTXpOR1ZmTmpJdWJYQTBJaUFkQUFDQVFDQUNLaENoT1h0R0VnMjNPV3duT3lra0lRRG1NZ1VOQUFDZ1FRLyROdW1iZXIkLm1wND9Qb2xpY3k9ZXlKVGRHRjBaVzFsYm5RaU9pQmJleUpTWlhOdmRYSmpaU0k2SW1oMGRIQnpPaTh2YzNBdFlXUXRZMll1WVhWa2FXOHVkR2xrWVd3dVkyOXRMMjFsWkdsaGRISmhZMnR6TDBkcGMwbEJlRWx1VDFkWk1FMVVhelZaZWxVd1drUkthbHBFYUdwT2JWRXpXbTFaZDA1WFJteE5WMVUxV21wTmVrNUhWbVpPYWtsMVlsaEJNRWxwUVdSQlFVTkJVVU5CUTB0b1EyaFBXSFJIUldjeU0wOVhkMjVQZVd0clNWRkViVTFuVlU1QlFVTm5VVkV2S2lJc0lrTnZibVJwZEdsdmJpSTZleUpFWVhSbFRHVnpjMVJvWVc0aU9uc2lRVmRUT2tWd2IyTm9WR2x0WlNJNk1UYzJOamczTURRM01uMTlmVjE5JmFtcDtTaWduYXR1cmU9dlh+dXBTalhCVVVUSjJnUzBkaE51a2NaMy1DSGhTTXdqM1MyM1l1czRqWjBFd0JTYmRCV09sZnluclpsTmJ0NldLdEIwODhqaWczOXdWLXh6REVMeUR5Z05OM29hOGZNNXA1VWhUN09CSlFnNkN+aUs5RGdxZXhPZGt2c3hKTG1ZTlBXUmMydkJLfkxkT2xtajVVcmxHZmxoWFB0WU5+NndoNGlkNzB5UHJZclZDR3RWSU9Wc2ZQMmp6R0QxTTNRMlU5MTBjbjlnT2FNeWlPWElLZ3A5eDF4RWo4RGVvUFQ2T2N4YjQtR35rQVMwYUw5SUhZTXZ+NkYzM1p1NUotSnUxSEJjdzJjR1dSMFVmYjRzNGVKRGhNZHVsR09YS0ZkTlVZZHR1amRnaXFwYklpV2o1VmlDYnhyWWtSUFRGdDl3Z3EtcjJ1UVhNcDhhSGc3djBWTldRX18mYW1wO0tleS1QYWlyLUlkPUsxNExaQ1o5UVVJNEpMIiBzdGFydE51bWJlcj0iMSI+PFNlZ21lbnRUaW1lbGluZT48UyBkPSIxNzYxMjgiIHI9IjM5Ii8+PFMgZD0iMTM3ODYwIi8+PC9TZWdtZW50VGltZWxpbmU+PC9TZWdtZW50VGVtcGxhdGU+PExhYmVsPkZMQUNfSElSRVM8L0xhYmVsPjwvUmVwcmVzZW50YXRpb24+PC9BZGFwdGF0aW9uU2V0PjwvUGVyaW9kPjwvTVBEPg==",
        "albumReplayGain": -8.91,
        "albumPeakAmplitude": 0.970377,
        "trackReplayGain": -8.91,
        "trackPeakAmplitude": 0.970377,
        "bitDepth": 24,
        "sampleRate": 44100
    }
}
```

Where `manifest` is base64 encoded MPD manifest (use `"manifestMimeType": "application/dash+xml"` to identify).

> [!NOTE]
>
> See [Track Flows/Playing a song](#) for how to handle MPD in the web.

###### Decoded Manifest (formatted)

```xml
<?xml version='1.0' encoding='UTF-8'?>
<MPD
	xmlns="urn:mpeg:dash:schema:mpd:2011"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xmlns:xlink="http://www.w3.org/1999/xlink"
	xmlns:cenc="urn:mpeg:cenc:2013" xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 DASH-MPD.xsd" profiles="urn:mpeg:dash:profile:isoff-main:2011" type="static" minBufferTime="PT3.993S" mediaPresentationDuration="PT2M42.879S">
	<Period id="0">
		<AdaptationSet id="0" contentType="audio" mimeType="audio/mp4" segmentAlignment="true">
			<Representation id="0" codecs="flac" bandwidth="1667553" audioSamplingRate="44100">
				<SegmentTemplate timescale="44100" initialization="https://sp-ad-cf.audio.tidal.com/mediatracks/GisIAxInOWY0MTk5YzU0ZDJjZDhjNmQ3ZmYwNWFlMWU5ZjMzNGVfNjIubXA0IiAdAACAQCACKhChOXtGEg23OWwnOykkIQDmMgUNAACgQQ/0.mp4?Policy=eyJTdGF0ZW1lbnQiOiBbeyJSZXNvdXJjZSI6Imh0dHBzOi8vc3AtYWQtY2YuYXVkaW8udGlkYWwuY29tL21lZGlhdHJhY2tzL0dpc0lBeEluT1dZME1UazVZelUwWkRKalpEaGpObVEzWm1Zd05XRmxNV1U1WmpNek5HVmZOakl1YlhBMElpQWRBQUNBUUNBQ0toQ2hPWHRHRWcyM09Xd25PeWtrSVFEbU1nVU5BQUNnUVEvKiIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2Njg3MDQ3Mn19fV19&amp;Signature=vX~upSjXBUUTJ2gS0dhNukcZ3-CHhSMwj3S23Yus4jZ0EwBSbdBWOlfynrZlNbt6WKtB088jig39wV-xzDELyDygNN3oa8fM5p5UhT7OBJQg6C~iK9DgqexOdkvsxJLmYNPWRc2vBK~LdOlmj5UrlGflhXPtYN~6wh4id70yPrYrVCGtVIOVsfP2jzGD1M3Q2U910cn9gOaMyiOXIKgp9x1xEj8DeoPT6Ocxb4-G~kAS0aL9IHYMv~6F33Zu5J-Ju1HBcw2cGWR0Ufb4s4eJDhMdulGOXKFdNUYdtujdgiqpbIiWj5ViCbxrYkRPTFt9wgq-r2uQXMp8aHg7v0VNWQ__&amp;Key-Pair-Id=K14LZCZ9QUI4JL" media="https://sp-ad-cf.audio.tidal.com/mediatracks/GisIAxInOWY0MTk5YzU0ZDJjZDhjNmQ3ZmYwNWFlMWU5ZjMzNGVfNjIubXA0IiAdAACAQCACKhChOXtGEg23OWwnOykkIQDmMgUNAACgQQ/$Number$.mp4?Policy=eyJTdGF0ZW1lbnQiOiBbeyJSZXNvdXJjZSI6Imh0dHBzOi8vc3AtYWQtY2YuYXVkaW8udGlkYWwuY29tL21lZGlhdHJhY2tzL0dpc0lBeEluT1dZME1UazVZelUwWkRKalpEaGpObVEzWm1Zd05XRmxNV1U1WmpNek5HVmZOakl1YlhBMElpQWRBQUNBUUNBQ0toQ2hPWHRHRWcyM09Xd25PeWtrSVFEbU1nVU5BQUNnUVEvKiIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2Njg3MDQ3Mn19fV19&amp;Signature=vX~upSjXBUUTJ2gS0dhNukcZ3-CHhSMwj3S23Yus4jZ0EwBSbdBWOlfynrZlNbt6WKtB088jig39wV-xzDELyDygNN3oa8fM5p5UhT7OBJQg6C~iK9DgqexOdkvsxJLmYNPWRc2vBK~LdOlmj5UrlGflhXPtYN~6wh4id70yPrYrVCGtVIOVsfP2jzGD1M3Q2U910cn9gOaMyiOXIKgp9x1xEj8DeoPT6Ocxb4-G~kAS0aL9IHYMv~6F33Zu5J-Ju1HBcw2cGWR0Ufb4s4eJDhMdulGOXKFdNUYdtujdgiqpbIiWj5ViCbxrYkRPTFt9wgq-r2uQXMp8aHg7v0VNWQ__&amp;Key-Pair-Id=K14LZCZ9QUI4JL" startNumber="1">
					<SegmentTimeline>
						<S d="176128" r="39"/>
						<S d="137860"/>
					</SegmentTimeline>
				</SegmentTemplate>
				<Label>FLAC_HIRES</Label>
			</Representation>
		</AdaptationSet>
	</Period>
</MPD>
```

### `GET /recommendations/`

#### Params

- `id`: `int` (required) - the Tidal ID of the track.

#### Response

##### Recommendations

`200 OK`

```json
{
  "version": "2.3",
  "data": {
    "limit": 20,
    "offset": 0,
    "totalNumberOfItems": 25,
    "items": [
      {
        "track": {
          "id": 70689598,
          "title": "Chasing Colors (feat. Noah Cyrus)",
          "duration": 195,
          "replayGain": -13.06,
          "peak": 0.988617,
          "allowStreaming": true,
          "streamReady": true,
          "payToStream": false,
          "adSupportedStreamReady": true,
          "djReady": true,
          "stemReady": false,
          "streamStartDate": "2017-02-24T00:00:00.000+0000",
          "premiumStreamingOnly": false,
          "trackNumber": 1,
          "volumeNumber": 1,
          "version": null,
          "popularity": 66,
          "copyright": "2017 Joytime Collective",
          "bpm": 150,
          "key": "Ab",
          "keyScale": "MINOR",
          "url": "http://www.tidal.com/track/70689598",
          "isrc": "TCACY1707257",
          "editable": false,
          "explicit": false,
          "audioQuality": "LOSSLESS",
          "audioModes": [
            "STEREO"
          ],
          "mediaMetadata": {
            "tags": [
              "LOSSLESS"
            ]
          },
          "upload": false,
          "accessType": "PUBLIC",
          "spotlighted": false,
          "artist": {
            "id": 8539374,
            "name": "Marshmello & Ookay",
            "handle": null,
            "type": "MAIN",
            "picture": null
          },
          "artists": [
            {
              "id": 8539374,
              "name": "Marshmello & Ookay",
              "handle": null,
              "type": "MAIN",
              "picture": null
            }
          ],
          "album": {
            "id": 70689597,
            "title": "Chasing Colors (feat. Noah Cyrus)",
            "cover": "ae714a47-be3b-490f-b6a6-5688fa58263b",
            "vibrantColor": "#61c4e2",
            "videoCover": null
          },
          "mixes": {
            "TRACK_MIX": "001869ef55d3f5ef71ad9f35382e48"
          }
        },
        "sources": [
          "SUGGESTED_TRACKS"
        ]
      },
      <truncated>
    ]
  }
}
```

### `GET /search/`

#### Params

Specify only **one** of the following - specifying more doesn't do anything.

- `s`: `str` - track query
- `a`: `str` - artist query
- `v`: `str` - video query (not tested, caution!)
- `p`: `str` - playlist query

#### Response

##### Track

`200 OK`

```json
{
  "version": "2.0",
  "data": {
    "limit": 25,
    "offset": 0,
    "totalNumberOfItems": 300,
    "items": [
      {
        "id": 396931358,
        "title": "Stained",
        "duration": 185,
        "replayGain": -11.66,
        "peak": 1,
        "allowStreaming": true,
        "streamReady": true,
        "payToStream": false,
        "adSupportedStreamReady": true,
        "djReady": true,
        "stemReady": false,
        "streamStartDate": "2024-11-15T00:00:00.000+0000",
        "premiumStreamingOnly": false,
        "trackNumber": 9,
        "volumeNumber": 1,
        "version": null,
        "popularity": 69,
        "copyright": "℗ 2024 Linkin Park, LLC under exclusive license to Warner Records Inc.",
        "bpm": 92,
        "key": "FSharp",
        "keyScale": "MAJOR",
        "url": "http://www.tidal.com/track/396931358",
        "isrc": "USWB12403471",
        "editable": false,
        "explicit": false,
        "audioQuality": "LOSSLESS",
        "audioModes": [
          "STEREO"
        ],
        "mediaMetadata": {
          "tags": [
            "LOSSLESS",
            "HIRES_LOSSLESS"
          ]
        },
        "upload": false,
        "accessType": null,
        "spotlighted": false,
        "artist": {
          "id": 14123,
          "name": "Linkin Park",
          "handle": null,
          "type": "MAIN",
          "picture": "fbd7e516-5e69-439d-babb-485b98f60f89"
        },
        "artists": [
          {
            "id": 14123,
            "name": "Linkin Park",
            "handle": null,
            "type": "MAIN",
            "picture": "fbd7e516-5e69-439d-babb-485b98f60f89"
          }
        ],
        "album": {
          "id": 396931349,
          "title": "From Zero",
          "cover": "3f49a481-68e5-46e4-a57a-5da8a75aa106",
          "vibrantColor": "#ddb4e8",
          "videoCover": null
        },
        "mixes": {
          "TRACK_MIX": "0019faa01a1a2bed8ba6074367187c"
        }
      },
      {
        "id": 4081586,
        "title": "Tear Stained Eye",
        "duration": 261,
        "replayGain": -9.62,
        "peak": 0.965942,
        "allowStreaming": true,
        "streamReady": true,
        "payToStream": false,
        "adSupportedStreamReady": true,
        "djReady": true,
        "stemReady": false,
        "streamStartDate": "2008-12-23T00:00:00.000+0000",
        "premiumStreamingOnly": false,
        "trackNumber": 3,
        "volumeNumber": 1,
        "version": null,
        "popularity": 65,
        "copyright": "℗ 1995 Warner Records Inc.",
        "bpm": 133,
        "key": "E",
        "keyScale": "MAJOR",
        "url": "http://www.tidal.com/track/4081586",
        "isrc": "USWB19400071",
        "editable": false,
        "explicit": false,
        "audioQuality": "LOSSLESS",
        "audioModes": [
          "STEREO"
        ],
        "mediaMetadata": {
          "tags": [
            "LOSSLESS"
          ]
        },
        "upload": false,
        "accessType": null,
        "spotlighted": false,
        "artist": {
          "id": 8415,
          "name": "Son Volt",
          "handle": null,
          "type": "MAIN",
          "picture": "e2232bf1-79bb-4d47-b1da-a01c065f0ea3"
        },
        "artists": [
          {
            "id": 8415,
            "name": "Son Volt",
            "handle": null,
            "type": "MAIN",
            "picture": "e2232bf1-79bb-4d47-b1da-a01c065f0ea3"
          }
        ],
        "album": {
          "id": 4081583,
          "title": "Trace",
          "cover": "dd01f581-fd3d-4f8a-884d-563603317610",
          "vibrantColor": "#FFFFFF",
          "videoCover": null
        },
        "mixes": {
          "TRACK_MIX": "0013bc8f4cb6d7f28c4cd5b0060383"
        }
      },
      <truncated>
    ]
  }
}
```

##### Artist

```json
{
  "version": "2.0",
  "data": {
    "artists": {
      "limit": 25,
      "offset": 0,
      "totalNumberOfItems": 73,
      "items": [
        {
          "id": 8812,
          "name": "Coldplay",
          "artistTypes": [
            "ARTIST",
            "CONTRIBUTOR"
          ],
          "url": "http://www.tidal.com/artist/8812",
          "picture": "b4579672-5b91-4679-a27a-288f097a4da5",
          "selectedAlbumCoverFallback": null,
          "popularity": 92,
          "artistRoles": [
            {
              "categoryId": -1,
              "category": "Artist"
            },
            {
              "categoryId": 1,
              "category": "Producer"
            },
            {
              "categoryId": 11,
              "category": "Performer"
            },
            {
              "categoryId": 2,
              "category": "Songwriter"
            },
            {
              "categoryId": 10,
              "category": "Production team"
            },
            {
              "categoryId": 99,
              "category": "Misc"
            }
          ],
          "mixes": {
            "ARTIST_MIX": "000d63462309f499a611e73b4992bd"
          },
          "handle": null,
          "userId": null,
          "spotlighted": false
        },
        {
          "id": 39476431,
          "name": "Coldplay Piano Covers",
          "artistTypes": [
            "ARTIST",
            "CONTRIBUTOR"
          ],
          "url": "http://www.tidal.com/artist/39476431",
          "picture": "3e88ec5b-0058-4185-8c1c-385098528f40",
          "selectedAlbumCoverFallback": "3e88ec5b-0058-4185-8c1c-385098528f40",
          "popularity": 28,
          "artistRoles": [
            {
              "categoryId": -1,
              "category": "Artist"
            }
          ],
          "mixes": {

          },
          "handle": null,
          "userId": null,
          "spotlighted": false
        },
        <truncated>
    ]
  }
}
```

This API also returning tracks is a known bug.


