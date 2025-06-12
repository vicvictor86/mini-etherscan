from fastapi import APIRouter, HTTPException

from app.application.transactions_application import get_transaction_by_hash_application
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
def get_transaction_by_hash(
    transaction_hash: str,
    # current_user: UserDTO = Depends(get_current_active_user),
    # db: Session = Depends(get_db),
):
    # if current_user.role != UserRole.admin.value:
    #     requests_filter_schema["user_id"] = current_user.id

    try:
        transaction_data = get_transaction_by_hash_application(
            transaction_hash=transaction_hash
        )

        return transaction_data
    except BlockNotFound:
        raise HTTPException(
            status_code=404, detail=f"Transaction {transaction_hash} not found"
        )
