from fastapi import APIRouter, Request
from app.models.candidate import CandidateCreate

router = APIRouter(prefix="/api")


@router.get("/add-candidate")
async def add_candidate(request: Request):
    # Manually enter the candidate's details
    candidate = CandidateCreate(
        name="Eliyana Maretasari, S.Pd",
    )

    # Save the validated data to MongoDB
    collection = request.app.state.db["candidates"]
    result = await collection.insert_one(candidate.model_dump())

    return {
        "message": "Candidate added successfully",
        "id": str(result.inserted_id),
        **candidate.model_dump(),
    }