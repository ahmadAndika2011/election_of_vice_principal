from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import DuplicateKeyError
from app.auth_service import check_csrf, now, require_user
from app.voting_service import ALREADY_VOTED, existing_vote

router = APIRouter(prefix="/api")


class ChooseCandidateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name_candidate: str = Field(min_length=1, max_length=200)
    voter_name: str | None = None


@router.get("/vote-status")
async def vote_status(request: Request, identity=Depends(require_user)):
    from fastapi.responses import JSONResponse
    user, _ = identity
    vote = await existing_vote(request.app.state.db, user)
    return JSONResponse({"has_voted": vote is not None,
                         "name_candidate": vote.get("name_candidate") if vote else None},
                        headers={"Cache-Control": "no-store"})


@router.post("/choose-candidate")
async def choose_candidate(body: ChooseCandidateBody, request: Request,
                           identity=Depends(require_user)):
    user, session = identity
    check_csrf(request, session)
    if body.voter_name is not None and body.voter_name != user["username"]:
        raise HTTPException(403, "Nama pemilih tidak sesuai pengguna yang login.")
    db = request.app.state.db
    if await existing_vote(db, user):
        raise HTTPException(409, ALREADY_VOTED)
    candidate = await db[request.app.state.auth_settings.candidates_collection].find_one(
        {"name": body.name_candidate})
    if not candidate:
        raise HTTPException(404, "Calon tidak ditemukan.")
    # Sumber identitas adalah sesi server, bukan nama dari browser.
    try:
        result = await db["votings"].insert_one({
            "name_candidate": candidate["name"],
            "candidate_id": str(candidate["_id"]),
            "voter_name": user["username"],
            "voter_id": str(user["_id"]),
            "created_at": now(),
        })
    except DuplicateKeyError:
        # Dua tab dapat melewati find_one bersamaan. Index unik adalah penentu.
        raise HTTPException(409, ALREADY_VOTED)
    return {"ok": True, "id": str(result.inserted_id)}
