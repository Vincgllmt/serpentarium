from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .mdns import start_mdns, stop_mdns
from .routers.emulators import router as emulators_router
from .routers.games import router as games_router

app = FastAPI(title="Serpentarium API")

app.add_middleware(
    CORSMiddleware,
    # localhost + plages d'IP privees (LAN) + serpentarium.local (mDNS), n'importe quel port
    allow_origin_regex=(
        r"http://(localhost|127\.0\.0\.1|serpentarium\.local"
        r"|192\.168\.\d{1,3}\.\d{1,3}"
        r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})"
        r"(:\d+)?"
    ),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    init_db()
    await start_mdns()


@app.on_event("shutdown")
async def on_shutdown():
    await stop_mdns()


app.include_router(games_router)
app.include_router(emulators_router)


@app.get("/health")
def health():
    return {"status": "ok"}
