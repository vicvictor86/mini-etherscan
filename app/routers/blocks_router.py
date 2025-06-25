from fastapi import APIRouter, Depends, HTTPException, Request

from app.application.blocks_application import (
    fetch_blocks_application,
    fetch_cross_dex_sandwiches_attack,
    fetch_multi_layered_burger_sandwiches,
    fetch_sandwiches_attack_by_block_number_application,
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
    "/",
    summary="Fetch the latests blocks.",
)
async def fetch_blocks(pagination_params: PaginationParams = Depends()):
    block_data = await fetch_blocks_application(
        page=pagination_params.page, per_page=pagination_params.per_page
    )

    return block_data


@router.get(
    "/{number}",
    summary="Search for a block by number.",
)
async def get_block_by_number(block_number: int):

    try:
        block_data = await get_block_by_number_application(block_number=block_number)

        return block_data
    except BlockNotFound:
        raise HTTPException(status_code=404, detail=f"Block #{block_number} not found")


# Block number to test: 16308191
@router.get(
    "/{number}/sandwich",
    summary="Search for sandwiches attack on the specific block.",
)
async def fetch_sandwiches_attack_by_block_number(request: Request, block_number: int):
    try:
        sandwich_attacks = await fetch_sandwiches_attack_by_block_number_application(
            request=request,
            block_number=block_number,
        )

        return sandwich_attacks
    except BlockNotFound:
        raise HTTPException(status_code=404, detail=f"Block #{block_number} not found")


@router.get(
    "/{number}/multiple_sandwich",
    summary="Search for multi laired sandwiches attack on the specific block.",
)
async def fetch_detect_multi_layered_burger_sandwiches_by_block_number(
    request: Request,
    block_number: int,
):
    try:
        sandwich_attacks = await fetch_multi_layered_burger_sandwiches(
            request=request,
            block_number=block_number,
        )

        return sandwich_attacks
    except BlockNotFound:
        raise HTTPException(status_code=404, detail=f"Block #{block_number} not found")


@router.get(
    "/{number}/cross_dex",
    summary="Search for cross dex laired sandwiches attack on the specific block.",
)
async def fetch_cross_dex_sandwiches_attack_by_block_number(
    request: Request,
    block_number: int,
):
    try:
        sandwich_attacks = await fetch_cross_dex_sandwiches_attack(
            request=request,
            block_number=block_number,
        )

        return sandwich_attacks
    except BlockNotFound:
        raise HTTPException(status_code=404, detail=f"Block #{block_number} not found")
