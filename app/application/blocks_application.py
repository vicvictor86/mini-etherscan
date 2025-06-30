from typing import Dict, List
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sandwich_attack_detector import (
    detect_cross_dex_sandwiches,
    detect_multi_layered_burger_sandwiches,
    detect_single_dex_sandwiches,
)
from app.application.swap_details import (
    get_all_swap_details_web3,
)
from app.application.web3_client.main import async_web3

from app.dbo.db_functions import (
    fetch_transactions_swap_by_block_number,
    fetch_transactions_swap_by_hash,
    get_analyzed_blocks_by_block_number,
    get_sandwich_attacks_by_block_grouped_by_attack_group,
    insert_block_analyzed,
    insert_transaction_swap,
)
from app.dto.schemas import TransactionSwapSchema
from app.utils.loggers import logger


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
    session: AsyncSession, block_number: int
):
    block_analyzed = await get_analyzed_blocks_by_block_number(
        session=session,
        block_number=block_number,
    )

    if block_analyzed:
        swaps_objects = await fetch_transactions_swap_by_block_number(
            session=session,
            block_number=block_number,
        )

        swaps = [
            TransactionSwapSchema.model_validate(s).model_dump(by_alias=True)
            for s in swaps_objects
        ]

        bloco_dict = {"number": block_number, "transactions": swaps}
    else:
        block = await async_web3.eth.get_block(block_number, full_transactions=False)
        tx_hashes = block["transactions"]
        print(len(tx_hashes), "transactions in block", block_number)

        swaps = []
        count = 0
        for hashes in tx_hashes:
            txh = hashes.hex() if hasattr(hashes, "hex") else hashes
            details = await get_all_swap_details_web3(
                async_web3=async_web3,
                tx_hash=txh,
                session=session,
                base_fee_per_gas=block.get("baseFeePerGas", None),
            )
            print(f"Finish swap detail for {txh} - count: {count}")
            count += 1
            if details:
                for detail in details:
                    await insert_transaction_swap(
                        session=session,
                        swap_data=detail,
                    )
                    swaps.append(detail)
            # if count >= 9:
            #     break

        bloco_dict = {"number": block_number, "transactions": swaps}

        await insert_block_analyzed(
            session=session,
            block_number=block_number,
        )

    detected = await detect_single_dex_sandwiches(session=session, block=bloco_dict)

    return {
        "block_number": block_number,
        "sandwiches": detected,
        "total_sandwiches": len(detected),
    }


async def fetch_multi_layered_burger_sandwiches(
    session: AsyncSession, block_number: int
):
    block = await async_web3.eth.get_block(block_number, full_transactions=False)
    tx_hashes = block["transactions"]
    print(len(tx_hashes), "transactions in block", block_number)

    swaps = []
    count = 0

    block_analyzed = await get_analyzed_blocks_by_block_number(
        session=session,
        block_number=block_number,
    )

    if block_analyzed:
        swaps = await fetch_transactions_swap_by_block_number(
            session=session,
            block_number=block_number,
        )
    else:
        for hashes in tx_hashes:
            txh = hashes.hex() if hasattr(hashes, "hex") else hashes

            # details = await fetch_transactions_swap_by_hash(
            #     session=session,
            #     hash_value=txh,
            # )

            details = await get_all_swap_details_web3(
                async_web3=async_web3,
                tx_hash=txh,
                session=session,
                base_fee_per_gas=block.get("baseFeePerGas", None),
            )

            if details:
                for detail in details:
                    await insert_transaction_swap(
                        session=session,
                        swap_data=detail,
                    )

            print(f"Finish swap detail for {txh} - count: {count}")

            # if count >= 3:
            #     break
            count += 1

        await insert_block_analyzed(session=session, block_number=block_number)
        swaps = await fetch_transactions_swap_by_block_number(
            session=session,
            block_number=block_number,
        )

    bloco_dict = {"number": block_number, "transactions": swaps}
    detected = await detect_multi_layered_burger_sandwiches(
        session=session,
        block=bloco_dict,
        base_fee_per_gas=block.get("baseFeePerGas", 0),
    )

    swap_dict = swaps
    if type(swaps[0]) is not dict:
        swap_dict = {f"{swap.hash}_{swap.log_index}": swap for swap in swaps}

    for attack in detected:
        # Busca os detalhes completos usando os hashes
        front_swap = []
        for hash_with_log_index in attack["front_run"]:
            front_swap.append(swap_dict.get(hash_with_log_index))

        back_swap = []
        for hash_with_log_index in attack["back_run"]:
            back_swap.append(swap_dict.get(hash_with_log_index))

        victims_swaps = [swap_dict.get(tx) for tx in attack["victims_txs"]]

        # Remove possíveis valores None (caso algum hash não esteja no swap_dict)
        victims_swaps = [s for s in victims_swaps if s is not None]

        attack["swaps"] = {
            "front_run": front_swap,
            "victims": victims_swaps,
            "back_run": back_swap,
        }

        del attack["front_run"]
        del attack["back_run"]
        del attack["victims_txs"]
        del attack["front_run_log_index"]
        del attack["back_run_log_index"]
        del attack["front_burned_eth"]
        del attack["front_tipped_eth"]
        del attack["back_burned_eth"]
        del attack["back_tipped_eth"]
        del attack["front_burned_usd"]
        del attack["front_tipped_usd"]
        del attack["back_burned_usd"]
        del attack["back_tipped_usd"]

    # await insert_block_analyzed(
    #     session=session,
    #     block_number=block_number,
    # )

    # attacks_info = await get_sandwich_attacks_by_block_grouped_by_attack_group(
    #     session=session,
    #     block_number=block_number,
    # )

    # attacks_info_grouped = group_by_attack_group_id(attacks_info)

    return {
        "block_number": block_number,
        "sandwiches": detected,
        "total_sandwiches": len(detected),
    }


# async def fetch_cross_dex_sandwiches_attack(session: AsyncSession, block_number: int):
#     block = await async_web3.eth.get_block(block_number, full_transactions=False)
#     tx_hashes = block["transactions"]
#     print(len(tx_hashes), "transactions in block", block_number)

#     swaps = []
#     count = 0
#     for hashes in tx_hashes:
#         txh = hashes.hex() if hasattr(hashes, "hex") else hashes

#         details = await fetch_transactions_swap_by_hash(
#             session=session,
#             hash_value=txh,
#         )

#         if len(details) == 0:
#             details = await get_all_swap_details_web3(
#                 async_web3=async_web3,
#                 tx_hash=txh,
#                 session=session,
#                 base_fee_per_gas=block.get("baseFeePerGas", None),
#             )

#             if details:
#                 for detail in details:
#                     await insert_transaction_swap(
#                         session=session,
#                         swap_data=detail,
#                     )

#         if details:
#             for detail in details:
#                 swaps.append(detail)
#         print(f"Finish swap detail for {txh} - count: {count}")
#         count += 1

#     bloco_dict = {"number": block_number, "transactions": swaps}
#     detected = await detect_cross_dex_sandwiches(bloco_dict)

#     # await insert_block_analyzed(
#     #     session=session,
#     #     block_number=block_number,
#     # )

#     # attacks_info = await get_sandwich_attacks_by_block_grouped_by_attack_group(
#     #     session=session,
#     #     block_number=block_number,
#     # )

#     # attacks_info_grouped = group_by_attack_group_id(attacks_info)

#     return {
#         "block_number": block_number,
#         "sandwiches": detected,
#         "total_sandwiches": len(detected),
#     }
