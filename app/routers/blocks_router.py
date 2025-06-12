from fastapi import APIRouter, Depends, HTTPException

from app.application.blocks_application import (
    fetch_blocks_application,
    get_block_by_number_application,
)
from app.dto.pagination_params import PaginationParams
from web3.exceptions import BlockNotFound

router = APIRouter(
    prefix="/blocks",
    tags=["Blocks"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/{number}",
    summary="Search for a block by number.",
)
async def get_block_by_number(
    block_number: int,
    # current_user: UserDTO = Depends(get_current_active_user),
    # db: Session = Depends(get_db),
):
    # if current_user.role != UserRole.admin.value:
    #     requests_filter_schema["user_id"] = current_user.id

    try:
        block_data = await get_block_by_number_application(block_number=block_number)

        return block_data
    except BlockNotFound:
        raise HTTPException(status_code=404, detail=f"Block #{block_number} not found")


@router.get(
    "/",
    summary="Fetch the latests blocks.",
)
async def fetch_blocks(
    pagination_params: PaginationParams = Depends(),
    # current_user: UserDTO = Depends(get_current_active_user),
    # db: Session = Depends(get_db),
):
    # if current_user.role != UserRole.admin.value:
    #     requests_filter_schema["user_id"] = current_user.id
    block_data = await fetch_blocks_application(
        page=pagination_params.page, per_page=pagination_params.per_page
    )

    return block_data
