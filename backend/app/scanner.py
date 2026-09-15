import re
import shutil
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

import py7zr
import rarfile

from .config import settings
from .db import get_connection

# rarfile ne fait qu'un wrapper autour d'un outil externe (pas d'implementation
# Python pure comme zipfile/py7zr) : il faut unrar/unar/7z installe sur la
# machine. On elargit un peu la recherche au cas ou WinRAR est installe sans
# etre sur le PATH.
if shutil.which("unrar") is None:
    for candidate in (
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
    ):
        if Path(candidate).exists():
            rarfile.UNRAR_TOOL = candidate
            break

# Extensions de ROMs reconnues -> plateforme. A completer selon ta collection.
ROM_EXTENSIONS = {
    ".nes": "Nintendo (NES)",
    ".sfc": "Super Nintendo",
    ".smc": "Super Nintendo",
    ".n64": "Nintendo 64",
    ".z64": "Nintendo 64",
    ".v64": "Nintendo 64",
    ".gb": "Game Boy",
    ".gbc": "Game Boy Color",
    ".gba": "Game Boy Advance",
    ".nds": "Nintendo DS",
    ".3ds": "Nintendo 3DS",
    ".nsp": "Nintendo Switch",
    ".xci": "Nintendo Switch",
    ".gcm": "GameCube",
    ".rvz": "GameCube / Wii",
    ".wbfs": "Wii",
    ".md": "Sega Genesis / Mega Drive",
    ".gen": "Sega Genesis / Mega Drive",
    ".chd": "Disque (CHD)",
    ".cue": "Disque (CUE/BIN)",
    ".iso": "Disque (ISO)",
}

ARCHIVE_EXTENSIONS = {".zip", ".7z", ".rar"}
CHUNK_SIZE = 1024 * 1024
CLEANUP_PATTERN = re.compile(r"[\(\[][^\)\]]*[\)\]]")


class MissingToolError(RuntimeError):
    """Un outil externe requis (unrar, ...) est absent de la machine."""


@dataclass
class RomEntry:
    name: str
    size: int
    crc32: str
    platform: str


def clean_title(filename: str) -> str:
    name = Path(filename).stem
    name = CLEANUP_PATTERN.sub("", name)
    name = name.replace("_", " ").replace(".", " ")
    return re.sub(r"\s+", " ", name).strip() or filename


def compute_crc32(path: Path) -> str:
    crc = 0
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            crc = zlib.crc32(chunk, crc)
    return format(crc & 0xFFFFFFFF, "08x")


def _best_rom_candidate(candidates: list[RomEntry]) -> RomEntry | None:
    return max(candidates, key=lambda c: c.size) if candidates else None


def _rom_in_zip(path: Path) -> RomEntry | None:
    candidates = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            platform = ROM_EXTENSIONS.get(Path(info.filename).suffix.lower())
            if platform is None:
                continue
            candidates.append(
                RomEntry(
                    name=Path(info.filename).name,
                    size=info.file_size,
                    crc32=format(info.CRC & 0xFFFFFFFF, "08x"),
                    platform=platform,
                )
            )
    return _best_rom_candidate(candidates)


def _rom_in_7z(path: Path) -> RomEntry | None:
    candidates = []
    with py7zr.SevenZipFile(path, "r") as archive:
        for info in archive.list():
            if info.is_directory:
                continue
            platform = ROM_EXTENSIONS.get(Path(info.filename).suffix.lower())
            if platform is None:
                continue
            candidates.append(
                RomEntry(
                    name=Path(info.filename).name,
                    size=info.uncompressed,
                    crc32=format(info.crc32 & 0xFFFFFFFF, "08x"),
                    platform=platform,
                )
            )
    return _best_rom_candidate(candidates)


def _rom_in_rar(path: Path) -> RomEntry | None:
    candidates = []
    with rarfile.RarFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            platform = ROM_EXTENSIONS.get(Path(info.filename).suffix.lower())
            if platform is None:
                continue
            candidates.append(
                RomEntry(
                    name=Path(info.filename).name,
                    size=info.file_size,
                    crc32=format(info.CRC & 0xFFFFFFFF, "08x"),
                    platform=platform,
                )
            )
    return _best_rom_candidate(candidates)


def _identify(path: Path) -> RomEntry | None:
    ext = path.suffix.lower()
    if ext in ARCHIVE_EXTENSIONS:
        try:
            if ext == ".zip":
                return _rom_in_zip(path)
            if ext == ".rar":
                return _rom_in_rar(path)
            return _rom_in_7z(path)
        except rarfile.RarCannotExec as exc:
            raise MissingToolError(
                "Impossible d'extraire les .rar : aucun outil unrar/WinRAR trouve. "
                "Installe WinRAR (https://www.win-rar.com/) ou unrar, puis reessaie."
            ) from exc
        except (zipfile.BadZipFile, py7zr.exceptions.Bad7zFile, rarfile.Error):
            return None

    platform = ROM_EXTENSIONS.get(ext)
    if platform is None:
        return None
    return RomEntry(name=path.name, size=path.stat().st_size, crc32=compute_crc32(path), platform=platform)


def _is_excluded(relative_parts: tuple[str, ...]) -> bool:
    return bool(relative_parts) and relative_parts[0].lower() == settings.emulators_dirname.lower()


def scan_roms() -> dict:
    roms_dir = Path(settings.roms_dir).resolve()
    if not roms_dir.exists():
        raise FileNotFoundError(f"Dossier ROMs introuvable: {roms_dir}")

    added = 0
    updated = 0
    skipped = 0

    with get_connection() as conn:
        for path in sorted(roms_dir.rglob("*")):
            if not path.is_file():
                continue

            relative = path.relative_to(roms_dir)
            if _is_excluded(relative.parts):
                continue

            rom = _identify(path)
            if rom is None:
                skipped += 1
                continue

            relpath = str(relative)
            # Certaines archives (surtout .rar) stockent le nom interne dans un
            # encodage corrompu (chars de remplacement irrecuperables) alors que
            # le nom du fichier sur le disque, lui, est toujours correct.
            display_name = path.name if "�" in rom.name else rom.name
            title = clean_title(display_name)

            existing = conn.execute(
                "SELECT id, crc32 FROM games WHERE relpath = ?", (relpath,)
            ).fetchone()

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO games (title, platform, filename, relpath, size, crc32)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (title, rom.platform, display_name, relpath, rom.size, rom.crc32),
                )
                added += 1
            elif existing["crc32"] != rom.crc32:
                conn.execute(
                    "UPDATE games SET size = ?, crc32 = ?, filename = ?, platform = ? WHERE id = ?",
                    (rom.size, rom.crc32, display_name, rom.platform, existing["id"]),
                )
                updated += 1

        total = conn.execute("SELECT COUNT(*) AS n FROM games").fetchone()["n"]

    return {"added": added, "updated": updated, "skipped": skipped, "total": total}
