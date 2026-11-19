import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from fastapi import HTTPException, Request
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from app.models.user import UserCreate
from app.models.session import SessionCreate


def now():
    return datetime.now(timezone.utc)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def init_auth_indexes(db):
    await db["users"].create_index("google_sub", unique=True)
    await db["users"].create_index("email", unique=True)
    # Banyak akun baru boleh memiliki username=None.
    await db["users"].create_index("username_key", unique=True,
        partialFilterExpression={"username_key": {"$type": "string"}})
    await db["sessions"].create_index("token_hash", unique=True)
    await db["sessions"].create_index("expires_at", expireAfterSeconds=0)


async def upsert_google_user(db, info):
    if info.get("email_verified") is not True or not info.get("sub") or not info.get("email"):
        raise HTTPException(403, "Email Google belum terverifikasi.")
    email = info["email"].strip().lower()
    record = UserCreate(google_sub=info["sub"], email=email, created_at=now()).model_dump(mode="python")
    # Email tidak menjadi kunci login: selalu identifikasi dengan Google sub.
    record.pop("email")
    try:
        return await db["users"].find_one_and_update(
            {"google_sub": info["sub"]},
            {"$set": {"email": email}, "$setOnInsert": record},
            upsert=True, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        existing = await db["users"].find_one({"google_sub": info["sub"]})
        if existing and existing["email"] == email:
            return existing  # Dua callback untuk akun yang sama.
        raise HTTPException(409, "Email sudah digunakan akun lain. Hubungi panitia.")


async def issue_session(request: Request, response, user):
    settings = request.app.state.auth_settings
    db = request.app.state.db
    old = request.cookies.get(settings.cookie_name)
    if old:
        await db["sessions"].delete_one({"token_hash": token_hash(old)})
    raw = secrets.token_urlsafe(32)
    seconds = settings.session_days * 86400 if user.get("username") else 900
    record = SessionCreate(token_hash=token_hash(raw), user_id=str(user["_id"]),
        csrf_token=secrets.token_urlsafe(32), created_at=now(),
        expires_at=now() + timedelta(seconds=seconds))
    await db["sessions"].insert_one(record.model_dump())
    response.set_cookie(settings.cookie_name, raw, max_age=seconds,
        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"


async def optional_identity(request: Request):
    settings = request.app.state.auth_settings
    raw = request.cookies.get(settings.cookie_name)
    if not raw or len(raw) > 256:
        return None
    db = request.app.state.db
    session = await db["sessions"].find_one({"token_hash": token_hash(raw), "expires_at": {"$gt": now()}})
    if not session or not ObjectId.is_valid(session["user_id"]):
        return None
    user = await db["users"].find_one({"_id": ObjectId(session["user_id"])})
    return (user, session) if user else None


async def require_identity(request: Request):
    identity = await optional_identity(request)
    if identity is None:
        raise HTTPException(401, "Silakan login melalui Google terlebih dahulu.")
    return identity


async def require_user(request: Request):
    user, session = await require_identity(request)
    if not user.get("username"):
        raise HTTPException(403, "Lengkapi username dengan nama lengkap terlebih dahulu.")
    return user, session


def check_csrf(request: Request, session):
    expected_origin = request.app.state.auth_settings.base_url
    origin = request.headers.get("origin")
    # Header token wajib, juga untuk klien yang tidak mengirim Origin.
    if origin is not None and origin != expected_origin:
        raise HTTPException(403, "Origin tidak diizinkan.")
    supplied = request.headers.get("x-csrf-token", "")
    if not secrets.compare_digest(supplied, session["csrf_token"]):
        raise HTTPException(403, "Token CSRF tidak valid. Muat ulang halaman.")
