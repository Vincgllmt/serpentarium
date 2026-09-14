from fastapi import APIRouter

from ..emulators import list_emulators
from ..schemas import EmulatorOut

router = APIRouter(prefix="/api")


@router.get("/emulators", response_model=list[EmulatorOut])
def get_emulators():
    return list_emulators()
