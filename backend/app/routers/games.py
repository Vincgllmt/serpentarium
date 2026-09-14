from fastapi import APIRouter, HTTPException

from ..db import get_connection
from ..schemas import GameOut, ScanResult
from ..scanner import scan_roms
from ..screenscraper import ScreenScraperError, fetch_game_info, resolve_systeme_id

router = APIRouter(prefix="/api")


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


@router.post("/scan", response_model=ScanResult)
def scan():
    try:
        return scan_roms()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/games/{game_id}/enrich", response_model=GameOut)
async def enrich_game(game_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Jeu introuvable")
        game = dict(row)

        try:
            systeme_id = await resolve_systeme_id(game["platform"])
            info = await fetch_game_info(
                crc32=game["crc32"],
                systeme_id=systeme_id,
                rom_name=game["filename"],
                rom_size=game["size"],
            )
        except ScreenScraperError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if info is None:
            raise HTTPException(status_code=404, detail="Jeu non trouve sur ScreenScraper")

        conn.execute(
            """
            UPDATE games
            SET title = COALESCE(?, title), cover_url = ?, ss_id = ?
            WHERE id = ?
            """,
            (info["title"], info["cover_url"], info["ss_id"], game_id),
        )
        updated = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()

    return dict(updated)
