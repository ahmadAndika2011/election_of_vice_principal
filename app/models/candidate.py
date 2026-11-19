from pydantic import BaseModel, Field


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class CandidateResponse(CandidateCreate):
    id: str