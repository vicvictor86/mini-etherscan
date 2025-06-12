from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated

from app.auth_middleware import get_current_active_user, get_token
from app.database import get_db
from app.dto.user_dto import UserDTO, UserResponse
from app.dto.token_dto import TokenDTO

router = APIRouter(
    prefix="/auth",
    tags=["Authorization"],
    responses={404: {"description": "Not found"}},
)


@router.post("/token", summary="Authorization")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
) -> TokenDTO:
    response = get_token(form_data, db)
    return response


@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Usuario logado.",
    tags=["Authorization"],
)
async def read_users_me(
    current_user: Annotated[UserDTO, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
):
    return current_user
