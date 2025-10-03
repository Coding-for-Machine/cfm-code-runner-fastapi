from fastapi import APIRouter


router = APIRouter()


@router.get("/language")
async def get_all_language():
    return {"langyage": {
        "python": True
    }}