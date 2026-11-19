from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()
TEMPLATE = Path(__file__).resolve().parents[1] / "templates/peringkat-kandidat.html"


@router.get("/peringkat-kandidat", include_in_schema=False)
async def ranking_page():
    return FileResponse(TEMPLATE, headers={"Cache-Control": "no-store"})
