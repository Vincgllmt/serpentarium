"""Client pour l'API ScreenScraper.fr (recuperation des jaquettes/metadonnees).

Necessite un compte developpeur (devid/devpassword, approuve manuellement par
l'equipe ScreenScraper) + un compte utilisateur (ssid/sspassword). Voir
backend/.env.example.

Notes issues de tests reels contre l'API (compte non-donateur, niveau 1) :
- api2.screenscraper.fr est en panne DNS ; www.screenscraper.fr sert le meme
  /api2/*, d'ou ss_base_url pointant dessus par defaut.
- Le compte n'a droit qu'a 1 thread en parallele (maxthreads=1) : toutes les
  requetes sont serialisees ici avec un delai mini entre deux appels.
- Les endpoints de recherche floue (jeuRecherche.php) peuvent etre lents/mis
  en file d'attente et timeout a 30s ; les lookups exacts (systemesListe,
  jeuInfos par crc) repondent vite. D'ou les retries avec timeout croissant.
- jeuInfos.php renvoie du texte brut (pas du JSON) + HTTP 404 quand la rom
  n'est pas trouvee, ex: "Erreur : Rom/Iso/Dossier non trouvee !".
"""

import asyncio
import difflib
import json
import re
import time
from pathlib import Path

import httpx

from .config import settings

SYSTEMS_CACHE = Path(settings.db_path).parent / "ss_systems.json"

# Priorite de region pour choisir la jaquette / le titre / la date a afficher
REGION_PRIORITY = ["wor", "eu", "us", "ss", "jp"]
COVER_MEDIA_TYPES = ["box-2D", "box-2d"]

_last_call_at = 0.0
_throttle_lock = asyncio.Lock()


class ScreenScraperError(RuntimeError):
    pass


class ScreenScraperQuotaError(ScreenScraperError):
    """Quota/threads depasse cote ScreenScraper : mieux vaut arreter le batch en cours."""


def _common_params() -> dict:
    return {
        "devid": settings.ss_devid,
        "devpassword": settings.ss_devpassword,
        "softname": settings.ss_softname,
        "ssid": settings.ss_ssid,
        "sspassword": settings.ss_sspassword,
        "output": "json",
    }


async def _throttle() -> None:
    """Garantit un delai mini entre deux requetes (compte limite a 1 thread)."""
    global _last_call_at
    async with _throttle_lock:
        wait = settings.ss_min_interval_seconds - (time.monotonic() - _last_call_at)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call_at = time.monotonic()


async def _request(path: str, params: dict) -> httpx.Response:
    """GET avec throttle + retries a timeout croissant (l'API peut mettre en
    file d'attente les comptes non-donateurs sous charge)."""
    last_error: Exception | None = None
    for attempt in range(1, settings.ss_max_retries + 1):
        await _throttle()
        timeout = settings.ss_timeout_seconds * attempt
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{settings.ss_base_url}{path}", params=params)
            # Codes documentes par ScreenScraper pour acces refuse / quota depasse.
            if resp.status_code in (429, 430, 431):
                raise ScreenScraperQuotaError(f"Quota/acces ScreenScraper refuse ({resp.status_code}) : {resp.text[:200]}")
            return resp
        except httpx.TimeoutException as exc:
            last_error = exc
            continue
    raise ScreenScraperError(f"ScreenScraper injoignable apres {settings.ss_max_retries} tentatives") from last_error


def _region_values(entries) -> dict[str, str]:
    """Normalise noms/dates en {region: text}, que l'API renvoie une liste de
    {region, text} ou un dict a plat (defensif, format non garanti partout)."""
    if isinstance(entries, dict):
        return {k: v for k, v in entries.items() if v}
    if isinstance(entries, list):
        return {e.get("region"): e.get("text") for e in entries if e.get("text")}
    return {}


async def _get_systems() -> list[dict]:
    if SYSTEMS_CACHE.exists():
        return json.loads(SYSTEMS_CACHE.read_text(encoding="utf-8"))

    resp = await _request("/systemesListe.php", _common_params())
    resp.raise_for_status()
    data = resp.json()

    systems = data.get("response", {}).get("systemes", [])
    SYSTEMS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SYSTEMS_CACHE.write_text(json.dumps(systems), encoding="utf-8")
    return systems


async def resolve_systeme_id(platform_name: str, extension: str | None = None) -> str | None:
    """Fait correspondre une plateforme locale a un systemeid ScreenScraper.

    Priorite a l'extension de fichier (champ `extensions` de chaque systeme
    cote SS) quand elle est unique a un seul systeme ; sinon repli sur un
    fuzzy-match du nom de plateforme.
    """
    systems = await _get_systems()

    if extension:
        ext = extension.lstrip(".").lower()
        matches = [s for s in systems if ext in (s.get("extensions") or "").lower().split(",")]
        if len(matches) == 1:
            return matches[0].get("id")

    candidates: dict[str, str] = {}
    for system in systems:
        system_id = system.get("id")
        for nom in _region_values(system.get("noms", {})).values():
            if nom:
                candidates[nom.lower()] = system_id

    close = difflib.get_close_matches(platform_name.lower(), candidates.keys(), n=1, cutoff=0.4)
    return candidates[close[0]] if close else None


def _pick_cover_url(medias: list[dict]) -> str | None:
    by_region = {(m.get("type"), m.get("region")): m.get("url") for m in medias}
    for media_type in COVER_MEDIA_TYPES:
        for region in REGION_PRIORITY:
            if url := by_region.get((media_type, region)):
                return url
    return None


def _pick_by_region(values: dict[str, str]) -> str | None:
    for region in REGION_PRIORITY:
        if value := values.get(region):
            return value
    return next(iter(values.values()), None)


def _pick_year(dates: list[dict] | dict) -> int | None:
    date_text = _pick_by_region(_region_values(dates))
    if not date_text:
        return None
    match = re.search(r"\d{4}", date_text)
    return int(match.group()) if match else None


async def fetch_game_info(
    crc32: str, systeme_id: str | None, rom_name: str, rom_size: int
) -> dict | None:
    if not settings.screenscraper_configured:
        raise ScreenScraperError("Identifiants ScreenScraper non configures (voir .env)")

    params = _common_params() | {
        "crc": crc32,
        "romnom": rom_name,
        "romtaille": rom_size,
    }
    if systeme_id:
        params["systemeid"] = systeme_id

    resp = await _request("/jeuInfos.php", params)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()

    jeu = data.get("response", {}).get("jeu")
    if not jeu:
        return None

    return {
        "title": _pick_by_region(_region_values(jeu.get("noms", []))) or rom_name,
        "cover_url": _pick_cover_url(jeu.get("medias", [])),
        "year": _pick_year(jeu.get("dates", [])),
        "ss_id": jeu.get("id"),
    }
