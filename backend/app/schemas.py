from pydantic import BaseModel


class GameOut(BaseModel):
    id: int
    title: str
    platform: str
    filename: str
    size: int
    crc32: str | None
    cover_url: str | None
    year: int | None
    source: str | None


class ScanResult(BaseModel):
    added: int
    updated: int
    skipped: int
    total: int


class EmulatorOut(BaseModel):
    name: str
    file_count: int
    size: int
