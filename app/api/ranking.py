from fastapi import APIRouter, Request, Response
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
