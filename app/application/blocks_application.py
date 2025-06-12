from concurrent.futures import ThreadPoolExecutor
from app.application.web3_client.main import async_web3
import asyncio

executor = ThreadPoolExecutor(max_workers=5)


async def get_block_by_number_application(block_number: int):
    block = await async_web3.eth.get_block(block_number, full_transactions=False)

    transactions_hashes = block["transactions"]

    receipt_tasks = [
        async_web3.eth.get_transaction_receipt(tx_hash)
        for tx_hash in transactions_hashes[:5]
    ]
    receipts = await asyncio.gather(*receipt_tasks)

    block_status = "success"
    for receipt in receipts:
        if not receipt or receipt.get("status") != 1:
            block_status = "pending"
            break

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
