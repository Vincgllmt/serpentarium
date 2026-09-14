from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .routers.emulators import router as emulators_router
from .routers.games import router as games_router

app = FastAPI(title="Serpentarium API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(games_router)
app.include_router(emulators_router)


@app.get("/health")
def health():
    return {"status": "ok"}
