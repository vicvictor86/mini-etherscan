from fastapi import APIRouter, HTTPException

from app.application.transactions_application import (
    fetch_latests_transactions_application,
    get_transaction_by_hash_application,
)
from web3.exceptions import BlockNotFound

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/{transaction_hash}",
    summary="Search for a transaction by hash.",
)
async def get_transaction_by_hash(transaction_hash: str):
    try:
        transaction_data = await get_transaction_by_hash_application(
            transaction_hash=transaction_hash
        )

        return transaction_data
    except BlockNotFound:
        raise HTTPException(
            status_code=404, detail=f"Transaction {transaction_hash} not found"
        )


@router.get(
    "/",
    summary="Fetch the latests transactions.",
)
async def fetch_latest_transactions(limit: int = 10):
    try:
        transactions = await fetch_latests_transactions_application(limit=limit)

        return transactions
    except BlockNotFound:
        raise HTTPException(status_code=404, detail="No transactions found")
