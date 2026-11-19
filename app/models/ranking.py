from datetime import datetime
from pydantic import BaseModel, Field


class CandidateRanking(BaseModel):
    candidate_id: str
    name: str
    total_votes: int = Field(ge=0)
    rank: int = Field(ge=1)
    percentage: float = Field(ge=0, le=100)


class RankingResponse(BaseModel):
    data: list[CandidateRanking]
    total_candidates: int
    total_votes: int
    recorded_votes: int
    unmatched_votes: int
    updated_at: datetime
