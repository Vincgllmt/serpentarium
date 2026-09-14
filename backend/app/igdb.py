"""Client pour IGDB (Twitch) - recherche de jeux par titre + jaquette.

Necessite un Client ID / Client Secret Twitch (console developpeur Twitch,
libre-service, pas de validation manuelle). Voir backend/.env.example.
"""

import time

import httpx

from .config import settings

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
API_URL = "https://api.igdb.com/v4/games"

_token_cache: dict = {"access_token": None, "expires_at": 0.0}


class IgdbError(RuntimeError):
    pass


async def _get_access_token() -> str:
    if _token_cache["access_token"] and _token_cache["expires_at"] > time.time() + 60:
        return _token_cache["access_token"]

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            TOKEN_URL,
            params={
                "client_id": settings.igdb_client_id,
                "client_secret": settings.igdb_client_secret,
                "grant_type": "client_credentials",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data["expires_in"]
    return _token_cache["access_token"]


def _cover_url(cover: dict | None) -> str | None:
    if not cover or not cover.get("url"):
        return None
    url = cover["url"].replace("t_thumb", "t_cover_big")
    return f"https:{url}" if url.startswith("//") else url


async def search_game(title: str) -> dict | None:
    if not settings.igdb_configured:
        raise IgdbError("Identifiants IGDB non configures (voir .env)")

    token = await _get_access_token()
    headers = {
        "Client-ID": settings.igdb_client_id,
        "Authorization": f"Bearer {token}",
    }
    escaped_title = title.replace('"', '\\"')
    body = f'search "{escaped_title}"; fields name,cover.url,first_release_date; limit 1;'

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(API_URL, headers=headers, content=body)
        resp.raise_for_status()
        results = resp.json()

    if not results:
        return None

    game = results[0]
    year = time.gmtime(game["first_release_date"]).tm_year if game.get("first_release_date") else None

    return {
        "title": game.get("name"),
        "cover_url": _cover_url(game.get("cover")),
        "year": year,
        "external_id": str(game["id"]) if game.get("id") is not None else None,
    }
