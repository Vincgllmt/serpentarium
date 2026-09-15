"""Cache disque pour les jaquettes : on telecharge une fois depuis la source
(ScreenScraper/IGDB) puis on sert le fichier local, pour ne pas taper le CDN
distant a chaque affichage de la bibliotheque par chaque client."""

import asyncio
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import settings

COVERS_DIR = Path(settings.covers_dir)
_download_lock = asyncio.Lock()

_CONTENT_TYPE_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


def _existing_cover(game_id: int) -> str | None:
    for path in COVERS_DIR.glob(f"{game_id}.*"):
        return f"/covers/{path.name}"
    return None


def _guess_extension(url: str, content_type: str | None) -> str:
    if content_type and (ext := _CONTENT_TYPE_EXT.get(content_type.split(";")[0].strip().lower())):
        return ext
    suffix = Path(urlparse(url).path).suffix.lstrip(".").lower()
    return suffix if suffix in _CONTENT_TYPE_EXT.values() else "jpg"


async def cache_cover(game_id: int, source_url: str, *, force: bool = False) -> str | None:
    """Retourne une URL locale (/covers/...) pour la jaquette de `game_id`,
    en la telechargeant une seule fois. Renvoie None si le telechargement
    echoue (l'appelant peut alors garder l'URL distante en repli)."""
    if not force:
        if cached := _existing_cover(game_id):
            return cached

    async with _download_lock:
        if not force:
            if cached := _existing_cover(game_id):
                return cached
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(source_url)
                resp.raise_for_status()
        except httpx.HTTPError:
            return None

        COVERS_DIR.mkdir(parents=True, exist_ok=True)
        for stale in COVERS_DIR.glob(f"{game_id}.*"):
            stale.unlink(missing_ok=True)

        ext = _guess_extension(source_url, resp.headers.get("content-type"))
        dest = COVERS_DIR / f"{game_id}.{ext}"
        dest.write_bytes(resp.content)
        return f"/covers/{dest.name}"
