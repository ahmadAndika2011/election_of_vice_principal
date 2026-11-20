from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.auth_service import check_csrf, require_identity
from app.models.ranking import RankingResponse
from app.voting_service import candidate_rankings

router = APIRouter(prefix="/api")


@router.get("/peringkat-kandidat", response_model=RankingResponse)
async def ranking(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return await candidate_rankings(
        request.app.state.db,
        request.app.state.auth_settings.candidates_collection,
    )


VOTE_ADMIN_EMAIL = "abdul.abdulrohim.rohim@gmail.com"


@router.get("/voting/izin-hapus")
async def deletion_permission(response: Response, identity=Depends(require_identity)):
    user, _ = identity
    response.headers["Cache-Control"] = "no-store"
    return {"allowed": user["email"] == VOTE_ADMIN_EMAIL}


@router.delete("/voting")
async def delete_votes(request: Request, identity=Depends(require_identity)):
    user, session = identity
    if user["email"] != VOTE_ADMIN_EMAIL:
        raise HTTPException(403, "Akun ini tidak memiliki izin menghapus suara.")
    check_csrf(request, session)
    result = await request.app.state.db["votings"].delete_many({})
    return {"deleted_count": result.deleted_count}
