from fastapi import APIRouter

router = APIRouter(
    prefix="/",
    tags=["Ping"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get("/ping")
async def ping():
    """
    Ping endpoint to check if the server is running.
    Returns a simple message indicating the server is alive.
    """
    return {"message": "pong"}


@router.get("")
async def root():
    """
    Root endpoint to check if the server is running.
    Returns a simple message indicating the server is alive.
    """
    return {"message": "Welcome to the MiniEtherscan API"}
