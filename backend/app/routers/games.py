import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from ..db import get_connection
from ..igdb import IgdbError, search_game
from ..schemas import GameOut, ScanResult
from ..scanner import scan_roms

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
            info = await search_game(game["title"])
        except IgdbError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if info is None:
            raise HTTPException(status_code=404, detail="Jeu non trouve sur IGDB")

        conn.execute(
            """
            UPDATE games
            SET title = COALESCE(?, title), cover_url = ?, year = ?, external_id = ?, source = 'igdb'
            WHERE id = ?
            """,
            (info["title"], info["cover_url"], info["year"], info["external_id"], game_id),
        )
        updated = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()

    return dict(updated)


@router.post("/enrich-all", response_model=list[GameOut])
async def enrich_all_games():
    with get_connection() as conn:
        ids = [row["id"] for row in conn.execute("SELECT id FROM games").fetchall()]

    results = []
    for game_id in ids:
        try:
            results.append(await enrich_game(game_id))
        except HTTPException:
            continue
        await asyncio.sleep(0.3)  # reste sous la limite de rate-limit IGDB (~4 req/s)
    return results
