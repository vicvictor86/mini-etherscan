from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.transactions_application import (
    fetch_latests_transactions_application,
    get_transaction_by_hash_application,
)
from web3.exceptions import BlockNotFound

from app.dto.transactions_response import TransactionResponse
from app.extension import get_db

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/{transaction_hash}",
    summary="Search for a transaction by hash.",
    response_model=TransactionResponse,
)
async def get_transaction_by_hash(
    transaction_hash: str,
    session: AsyncSession = Depends(get_db),
):
    try:
        transaction_data = await get_transaction_by_hash_application(
            session=session, transaction_hash=transaction_hash
        )

        return transaction_data
    except BlockNotFound:
        raise HTTPException(
            status_code=404, detail=f"Transaction {transaction_hash} not found"
        )


@router.get(
    "/",
    summary="Fetch the latests transactions.",
    response_model=list[TransactionResponse],
)
async def fetch_latest_transactions(
    session: AsyncSession = Depends(get_db),
    limit: int = 10,
):
    try:
        transactions = await fetch_latests_transactions_application(
            limit=limit, session=session
        )

        return transactions
    except BlockNotFound:
        raise HTTPException(status_code=404, detail="No transactions found")
