from pathlib import Path
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from authlib.integrations.base_client.errors import OAuthError
from joserfc.errors import JoseError
from httpx import HTTPError
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from app.auth_service import (check_csrf, issue_session, optional_identity,
    require_identity, token_hash, upsert_google_user)
from app.models.user import CompleteProfile, UserResponse, username_key

router = APIRouter()
ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)


@router.get("/auth/login", include_in_schema=False)
@router.get("/auth/signup", include_in_schema=False)
async def login_page():
    return FileResponse(ROOT / "templates/auth.html", headers={"Cache-Control": "no-store"})


@router.get("/auth/complete-profile", include_in_schema=False)
async def profile_page(request: Request):
    identity = await optional_identity(request)
    if not identity:
        return RedirectResponse("/auth/login", status_code=303)
    if identity[0].get("username"):
        return RedirectResponse("/", status_code=303)
    return FileResponse(ROOT / "templates/complete-profile.html", headers={"Cache-Control": "no-store"})


@router.get("/auth/client.js", include_in_schema=False)
async def client_script():
    return FileResponse(ROOT / "assets/js/auth.js", media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"})


@router.get("/auth/google", include_in_schema=False)
async def google_start(request: Request):
    settings = request.app.state.auth_settings
    request.session.clear()
    return await request.app.state.oauth.google.authorize_redirect(
        request, settings.base_url + "/auth/google/callback", prompt="select_account")


@router.get("/auth/google/callback", include_in_schema=False)
async def google_callback(request: Request):
    try:
        # Authlib memvalidasi OAuth state, nonce dan ID token Google.
        token = await request.app.state.oauth.google.authorize_access_token(request)
        info = token.get("userinfo")
        if not info:
            raise HTTPException(403, "Identitas Google tidak tersedia.")
        user = await upsert_google_user(request.app.state.db, info)
    except (OAuthError, JoseError, HTTPError, HTTPException, ValueError) as exc:
        # Jangan mencatat token/kode otorisasi dari exception provider.
        logger.warning("Google login rejected: %s", type(exc).__name__)
        response = RedirectResponse("/auth/login?error=google_login_failed", status_code=303)
    else:
        response = RedirectResponse("/" if user.get("username") else "/auth/complete-profile", status_code=303)
        await issue_session(request, response, user)
    finally:
        request.session.clear()  # Tidak menyimpan access_token Google dalam cookie.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get("/api/auth/me")
async def me(request: Request):
    identity = await optional_identity(request)
    if not identity:
        return JSONResponse({"authenticated": False, "user": None, "csrf_token": None},
                            headers={"Cache-Control": "no-store"})
    user, session = identity
    public = UserResponse(id=str(user["_id"]), email=user["email"], username=user.get("username"))
    return JSONResponse({"authenticated": True, "profile_complete": bool(user.get("username")),
                         "user": public.model_dump(mode="json"), "csrf_token": session["csrf_token"]},
                        headers={"Cache-Control": "no-store"})


@router.post("/api/auth/complete-profile")
async def complete_profile(body: CompleteProfile, request: Request,
                           identity=Depends(require_identity)):
    user, session = identity
    check_csrf(request, session)
    if user.get("username"):
        raise HTTPException(409, "Profil sudah lengkap.")
    try:
        updated = await request.app.state.db["users"].find_one_and_update(
            {"_id": user["_id"], "username": None},
            {"$set": {"username": body.username, "username_key": username_key(body.username)}},
            return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        raise HTTPException(409, "username is exist")
    if updated is None:
        raise HTTPException(409, "Profil sudah lengkap.")
    response = JSONResponse({"ok": True, "username": updated["username"]})
    # Rotasi token dan perpanjang sesi setelah signup selesai.
    await issue_session(request, response, updated)
    return response


@router.post("/api/auth/logout")
async def logout(request: Request, identity=Depends(require_identity)):
    _, session = identity
    check_csrf(request, session)
    settings = request.app.state.auth_settings
    raw = request.cookies.get(settings.cookie_name, "")
    await request.app.state.db["sessions"].delete_one({"token_hash": token_hash(raw)})
    request.session.clear()
    response = JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})
    response.delete_cookie(settings.cookie_name, path="/", secure=settings.cookie_secure,
                           httponly=True, samesite="lax")
    return response
