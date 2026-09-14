from pathlib import Path

from .config import settings


def list_emulators() -> list[dict]:
    base = Path(settings.roms_dir).resolve() / settings.emulators_dirname
    if not base.exists():
        return []

    emulators = []
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        files = [f for f in folder.rglob("*") if f.is_file()]
        emulators.append(
            {
                "name": folder.name,
                "file_count": len(files),
                "size": sum(f.stat().st_size for f in files),
            }
        )
    return emulators
