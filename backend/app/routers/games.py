import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from ..db import get_connection
from ..igdb import IgdbError, search_game
from ..media_cache import cache_cover
from ..schemas import GameOut, ScanResult
from ..scanner import MissingToolError, scan_roms
from ..screenscraper import ScreenScraperError, ScreenScraperQuotaError, fetch_game_info, resolve_systeme_id

router = APIRouter(prefix="/api")


async def _fetch_scrape_info(game: dict) -> tuple[dict, str] | None:
    """Essaie ScreenScraper (match exact par CRC32) puis IGDB (recherche par
    titre) en repli. Renvoie (info, source) ou None si rien trouve."""
    if settings.screenscraper_configured and game["crc32"]:
        extension = Path(game["filename"]).suffix
        systeme_id = await resolve_systeme_id(game["platform"], extension)
        try:
            info = await fetch_game_info(game["crc32"], systeme_id, game["filename"], game["size"])
        except ScreenScraperQuotaError:
            raise
        except ScreenScraperError:
            info = None
        if info is not None:
            return info, "screenscraper"

    if settings.igdb_configured:
        info = await search_game(game["title"])
        if info is not None:
            return info, "igdb"

    return None


async def _enrich_game(game_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Jeu introuvable")
        game = dict(row)

    result = await _fetch_scrape_info(game)
    if result is None:
        raise HTTPException(status_code=404, detail="Jeu non trouve (ScreenScraper/IGDB)")
    info, source = result

    cover_url = info.get("cover_url")
    if cover_url:
        cover_url = await cache_cover(game_id, cover_url) or cover_url

    external_id = info.get("ss_id") or info.get("external_id")

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE games
            SET title = COALESCE(?, title), cover_url = ?, year = ?, external_id = ?,
                source = ?, scraped_at = ?
            WHERE id = ?
            """,
            (
                info.get("title"),
                cover_url,
                info.get("year"),
                str(external_id) if external_id is not None else None,
                source,
                datetime.now(timezone.utc).isoformat(),
                game_id,
            ),
        )
        updated = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()

    return dict(updated)


@router.get("/games", response_model=list[GameOut])
def list_games():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM games ORDER BY title").fetchall()
    return [dict(row) for row in rows]


@router.get("/games/{game_id}", response_model=GameOut)
def get_game(game_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Jeu introuvable")
    return dict(row)


@router.get("/games/{game_id}/download")
def download_game(game_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Jeu introuvable")

    path = Path(settings.roms_dir).resolve() / row["relpath"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le disque")

    return FileResponse(path, filename=path.name, media_type="application/octet-stream")


@router.post("/scan", response_model=ScanResult)
def scan():
    try:
        return scan_roms()
    except (FileNotFoundError, MissingToolError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/games/{game_id}/enrich", response_model=GameOut)
async def enrich_game(game_id: int, force: bool = False):
    with get_connection() as conn:
        row = conn.execute("SELECT cover_url FROM games WHERE id = ?", (game_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Jeu introuvable")
    if row["cover_url"] and not force:
        with get_connection() as conn:
            return dict(conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone())

    try:
        return await _enrich_game(game_id)
    except ScreenScraperQuotaError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except IgdbError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/enrich-all", response_model=list[GameOut])
async def enrich_all_games(force: bool = False):
    """Ne re-scrape que les jeux sans jaquette (cache-first) sauf si force=true.
    S'arrete des qu'un quota ScreenScraper est atteint plutot que de continuer
    a marteler l'API."""
    with get_connection() as conn:
        query = "SELECT id FROM games" if force else "SELECT id FROM games WHERE cover_url IS NULL"
        ids = [row["id"] for row in conn.execute(query).fetchall()]

    results = []
    for game_id in ids:
        try:
            results.append(await _enrich_game(game_id))
        except ScreenScraperQuotaError:
            break
        except (HTTPException, IgdbError):
            continue
        await asyncio.sleep(0.3)  # reste sous la limite de rate-limit IGDB (~4 req/s)
    return results
