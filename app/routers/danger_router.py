from app.database import restart_db
from fastapi import APIRouter

router = APIRouter(
    prefix="/danger",
    tags=["DANGER"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.delete(
    "/database",
    summary="Delete the database and start over",
)
async def get_address(password: str):
    if password == "comp_aplicada_senha":
        await restart_db()
        return {"message": "Database reset successfully"}
    else:
        return {"message": "Invalid password"}, 403
