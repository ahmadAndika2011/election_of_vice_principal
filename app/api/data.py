import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api")

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "data.json"

@router.get("/data")
def data():
    with DATA_FILE.open("r", encoding="utf=8") as file:
        data = json.load(file)

    return data