from fastapi import APIRouter, Depends, HTTPException

from app.application.address_application import (
    fetch_txs_from_etherscan_application,
    get_address_application,
)
from app.application.blocks_application import get_block_by_number_application
from app.application.transactions_application import get_transaction_by_hash_application
from app.auth_middleware import get_current_active_user
from app.dto.user_dto import UserDTO
from app.application.web3_client.main import w3
from web3.exceptions import BlockNotFound

router = APIRouter(
    prefix="/address",
    tags=["Address"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/{address}",
    summary="Search for a account address",
)
def get_address(
    address: str,
    # current_user: UserDTO = Depends(get_current_active_user),
    # db: Session = Depends(get_db),
):
    # if current_user.role != UserRole.admin.value:
    #     requests_filter_schema["user_id"] = current_user.id

    return get_address_application(address=address)


@router.get(
    "/{address}/transactions",
    summary="Fetch account address transactions",
)
def get_address(
    address: str,
    startblock: int = 0,
    endblock: int = 99999999,
    page: int = 1,
    per_page: int = 10,
    # current_user: UserDTO = Depends(get_current_active_user),
    # db: Session = Depends(get_db),
):
    # if current_user.role != UserRole.admin.value:
    #     requests_filter_schema["user_id"] = current_user.id

    return fetch_txs_from_etherscan_application(
        address=address,
        startblock=startblock,
        endblock=endblock,
        page=page,
        per_page=per_page,
    )
