from fastapi import APIRouter

from app.application.address_application import (
    fetch_txs_from_etherscan_application,
    get_address_application,
)

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
def get_address(address: str):
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
):
    return fetch_txs_from_etherscan_application(
        address=address,
        startblock=startblock,
        endblock=endblock,
        page=page,
        per_page=per_page,
    )
