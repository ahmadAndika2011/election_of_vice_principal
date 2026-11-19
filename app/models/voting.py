from pydantic import Field, BaseModel

class VotingCreate(BaseModel):
    name_candidate: str = Field(min_length=1, max_length=200)
    voter_name: str = Field(min_length=1, max_length=200)

class VotingResponse(VotingCreate):
    id: str