"""Client pour l'API ScreenScraper.fr (recuperation des jaquettes/metadonnees).

Necessite un compte developpeur (devid/devpassword, approuve manuellement par
l'equipe ScreenScraper) + un compte utilisateur (ssid/sspassword). Voir
backend/.env.example.

Le format exact des reponses n'a pas ete verifie contre l'API reelle (pas de
compte dev disponible au moment de l'ecriture) : a ajuster une fois les
identifiants obtenus si des champs different de la doc officielle.
"""

import difflib
import json
from pathlib import Path

import httpx

from .config import settings

BASE_URL = "https://api2.screenscraper.fr/api2"
SYSTEMS_CACHE = Path(settings.db_path).parent / "ss_systems.json"

# Priorite de region pour choisir la jaquette a afficher
REGION_PRIORITY = ["wor", "eu", "us", "ss", "jp"]
COVER_MEDIA_TYPES = ["box-2D", "box-2d"]


class ScreenScraperError(RuntimeError):
    pass


def _common_params() -> dict:
    return {
        "devid": settings.ss_devid,
        "devpassword": settings.ss_devpassword,
        "softname": settings.ss_softname,
        "ssid": settings.ss_ssid,
        "sspassword": settings.ss_sspassword,
        "output": "json",
    }


async def _get_systems() -> list[dict]:
    if SYSTEMS_CACHE.exists():
        return json.loads(SYSTEMS_CACHE.read_text(encoding="utf-8"))

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/systemesListe.php", params=_common_params())
        resp.raise_for_status()
        data = resp.json()

    systems = data.get("response", {}).get("systemes", [])
    SYSTEMS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SYSTEMS_CACHE.write_text(json.dumps(systems), encoding="utf-8")
    return systems


async def resolve_systeme_id(platform_name: str) -> str | None:
    """Fait correspondre un nom de plateforme local a un systemeid ScreenScraper."""
    systems = await _get_systems()

    candidates: dict[str, str] = {}
    for system in systems:
        system_id = system.get("id")
        noms = system.get("noms", {})
        for nom in noms.values() if isinstance(noms, dict) else []:
            if nom:
                candidates[nom.lower()] = system_id

    matches = difflib.get_close_matches(platform_name.lower(), candidates.keys(), n=1, cutoff=0.4)
    return candidates[matches[0]] if matches else None


def _pick_cover_url(medias: list[dict]) -> str | None:
    by_region = {(m.get("type"), m.get("region")): m.get("url") for m in medias}
    for media_type in COVER_MEDIA_TYPES:
        for region in REGION_PRIORITY:
            if url := by_region.get((media_type, region)):
                return url
    return None


def _pick_title(noms: list[dict]) -> str | None:
    by_region = {n.get("region"): n.get("text") for n in noms}
    for region in REGION_PRIORITY:
        if title := by_region.get(region):
            return title
    return noms[0]["text"] if noms else None


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

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/jeuInfos.php", params=params)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

    jeu = data.get("response", {}).get("jeu")
    if not jeu:
        return None

    return {
        "title": _pick_title(jeu.get("noms", [])),
        "cover_url": _pick_cover_url(jeu.get("medias", [])),
        "year": None,
        "ss_id": jeu.get("id"),
    }
