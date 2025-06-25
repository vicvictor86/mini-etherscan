from typing import Dict, List
from fastapi import Request
import asyncio

from app.application.sandwich_attack_detector import (
    detect_cross_dex_sandwiches,
    detect_multi_layered_burger_sandwiches,
    detect_single_dex_sandwiches,
)
from app.application.swap_details import get_swap_details_web3
from app.application.web3_client.main import async_web3
from app.dbo.sandwiches_attacks_db import (
    get_analyzed_blocks_by_block_number,
    get_attack_groups_by_block,
    get_sandwich_attacks_by_block_grouped_by_attack_group,
    get_transaction_swap_by_hash,
    insert_block_analyzed,
    insert_transaction_swap,
)


async def get_block_by_number_application(block_number: int):
    block = await async_web3.eth.get_block(block_number, full_transactions=False)

    transactions_hashes = block["transactions"]

    finalized_head = await async_web3.eth.get_block("finalized")
    if block_number <= finalized_head["number"]:
        block_status = "finalized"
    else:
        block_status = "not_finalized"

    block_data = {
        "hash": block["hash"].hex(),
        "number": block["number"],
        "nonce": block["nonce"],
        "miner": block["miner"],
        "parent_hash": block["parentHash"].hex(),
        "timestamp": block["timestamp"],
        "status": block_status,
        "size": block.get("size", 0),
        "gas_used": block["gasUsed"],
        "base_fee_per_gas": block.get("baseFeePerGas"),
        "gas_limit": block["gasLimit"],
        "difficulty": block.get("difficulty", 0),
        "total_difficulty": block.get("totalDifficulty", 0),
        "withdrawals": block.get("withdrawals", []),
        "extra_data": block.get("extraData", "").hex(),
        "transactions_hashes": [tx.hex() for tx in transactions_hashes],
    }

    return block_data


async def fetch_blocks_application(page: int, per_page: int):
    latest_block = await async_web3.eth.get_block("latest")
    latest_block_number = latest_block["number"]

    start_block = max(0, latest_block_number - (page - 1) * per_page)
    end_block = max(0, latest_block_number - page * per_page)

    block_numbers = list(range(start_block, end_block, -1))
    fetch_tasks = [
        get_block_by_number_application(block_number) for block_number in block_numbers
    ]

    blocks = await asyncio.gather(*fetch_tasks)

    return {
        "blocks": blocks,
        "total_blocks": latest_block_number + 1,
        "current_page": page,
        "per_page": per_page,
    }


def group_by_attack_group_id(attacks_info: List[Dict]):
    groups: dict[int, dict] = {}
    for row in attacks_info:
        gid = row["attack_group_id"]
        if gid not in groups:
            groups[gid] = {
                "attack_group_id": gid,
                "block_number": row["block_number"],
                "ta1": row["ta1"],
                "tv": row["tv"],
                "ta2": row["ta2"],
                "swaps": [],
            }

        groups[gid]["swaps"].append(
            {
                "hash": row["hash"],
                "from_address": row["from_address"],
                "to_address": row["to_address"],
                "token_in": row["token_in"],
                "token_out": row["token_out"],
                "amount_in": row["amount_in"],
                "amount_out": row["amount_out"],
                "gas_price": row["gas_price"],
                "transition_type": row["transition_type"],
            }
        )

    return list(groups.values())


async def fetch_sandwiches_attack_by_block_number_application(
    request: Request, block_number: int
):
    block_analyzed = await get_analyzed_blocks_by_block_number(
        request=request,
        block_number=block_number,
    )

    if block_analyzed:
        attacks_info = await get_sandwich_attacks_by_block_grouped_by_attack_group(
            request=request,
            block_number=block_number,
        )
    else:
        block = await async_web3.eth.get_block(block_number, full_transactions=False)
        tx_hashes = block["transactions"]
        print(len(tx_hashes), "transactions in block", block_number)

        swaps = []
        count = 0
        for hashes in tx_hashes:
            txh = hashes.hex() if hasattr(hashes, "hex") else hashes
            detail = await get_swap_details_web3(async_web3=async_web3, tx_hash=txh)
            print(f"Finish swap detail for {txh} - count: {count}")
            count += 1
            if detail:
                swaps.append(detail)
            if count >= 9:
                break
        print(len(swaps))

        bloco_dict = {"number": block_number, "transactions": swaps}
        await detect_single_dex_sandwiches(request, bloco_dict)

        await insert_block_analyzed(
            request=request,
            block_number=block_number,
        )

        attacks_info = await get_sandwich_attacks_by_block_grouped_by_attack_group(
            request=request,
            block_number=block_number,
        )

    attacks_info_grouped = group_by_attack_group_id(attacks_info)

    return {
        "block_number": block_number,
        "sandwiches": attacks_info_grouped,
        "total_sandwiches": len(attacks_info_grouped),
    }


async def fetch_multi_layered_burger_sandwiches(request: Request, block_number: int):
    block = await async_web3.eth.get_block(block_number, full_transactions=False)
    tx_hashes = block["transactions"]
    print(len(tx_hashes), "transactions in block", block_number)

    swaps = []
    count = 0
    for hashes in tx_hashes:
        txh = hashes.hex() if hasattr(hashes, "hex") else hashes

        detail = await get_transaction_swap_by_hash(
            request=request,
            hash_value=txh,
        )

        if not detail:
            detail = await get_swap_details_web3(
                async_web3=async_web3,
                tx_hash=txh,
                request=request,
            )

            if detail:
                asyncio.create_task(
                    insert_transaction_swap(
                        request=request,
                        swap_data=detail,
                    )
                )

        if detail:
            swaps.append(detail)
        print(f"Finish swap detail for {txh} - count: {count}")
        count += 1

    bloco_dict = {"number": block_number, "transactions": swaps}
    detected = await detect_multi_layered_burger_sandwiches(request, bloco_dict)

    # await insert_block_analyzed(
    #     request=request,
    #     block_number=block_number,
    # )

    # attacks_info = await get_sandwich_attacks_by_block_grouped_by_attack_group(
    #     request=request,
    #     block_number=block_number,
    # )

    # attacks_info_grouped = group_by_attack_group_id(attacks_info)

    return {
        "block_number": block_number,
        "sandwiches": detected,
        "total_sandwiches": len(detected),
    }


async def fetch_cross_dex_sandwiches_attack(request: Request, block_number: int):
    block = await async_web3.eth.get_block(block_number, full_transactions=False)
    tx_hashes = block["transactions"]
    print(len(tx_hashes), "transactions in block", block_number)

    swaps = []
    count = 0
    for hashes in tx_hashes:
        txh = hashes.hex() if hasattr(hashes, "hex") else hashes

        detail = await get_transaction_swap_by_hash(
            request=request,
            hash_value=txh,
        )

        if not detail:
            detail = await get_swap_details_web3(
                async_web3=async_web3,
                tx_hash=txh,
                request=request,
            )

            if detail:
                asyncio.create_task(
                    insert_transaction_swap(
                        request=request,
                        swap_data=detail,
                    )
                )

        if detail:
            swaps.append(detail)
        print(f"Finish swap detail for {txh} - count: {count}")
        count += 1

    bloco_dict = {"number": block_number, "transactions": swaps}
    detected = await detect_cross_dex_sandwiches(bloco_dict)

    # await insert_block_analyzed(
    #     request=request,
    #     block_number=block_number,
    # )

    # attacks_info = await get_sandwich_attacks_by_block_grouped_by_attack_group(
    #     request=request,
    #     block_number=block_number,
    # )

    # attacks_info_grouped = group_by_attack_group_id(attacks_info)

    return {
        "block_number": block_number,
        "sandwiches": detected,
        "total_sandwiches": len(detected),
    }
