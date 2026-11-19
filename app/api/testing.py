from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.get("/check")
def check():
    return {"ok": True}

