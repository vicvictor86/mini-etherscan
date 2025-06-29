from sqlalchemy.ext.asyncio import AsyncSession
from hexbytes import HexBytes
import asyncio

from app.application.swap_details import (
    get_swap_details_web3,
)
from app.application.web3_client.main import async_web3


def _to_hex(value):
    """
    Converte HexBytes ou bytes em string hex com '0x...'
    Senao, retorna o valor original.
    """
    if isinstance(value, (HexBytes, bytes)):
        return value.hex()
    return value


async def get_transaction_by_hash_application(
    transaction_hash: str, session: AsyncSession
):
    tx_task = asyncio.create_task(async_web3.eth.get_transaction(transaction_hash))
    receipt_task = asyncio.create_task(
        async_web3.eth.get_transaction_receipt(transaction_hash)
    )
    transaction, receipt = await asyncio.gather(tx_task, receipt_task)

    swap_details = await get_swap_details_web3(
        async_web3=async_web3,
        tx_hash=transaction_hash,
        session=session,
        tx=transaction,
        receipt=receipt,
    )

    block = await async_web3.eth.get_block(transaction["blockNumber"])

    transaction_status = "Success" if receipt["status"] == 1 else "Failed"

    # Função auxiliar para aplicar _to_hex recursivamente em dicionários/listas
    def apply_to_hex(obj):
        if isinstance(obj, dict):
            return {k: apply_to_hex(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [apply_to_hex(item) for item in obj]
        else:
            return _to_hex(obj)

    transaction_data = {
        "transaction_hash": _to_hex(transaction["hash"]),
        "transaction_index": _to_hex(transaction["transactionIndex"]),
        "block_hash": (
            _to_hex(transaction["blockHash"]) if transaction["blockHash"] else None
        ),
        "block_number": _to_hex(transaction["blockNumber"]),
        "timestamp": _to_hex(block["timestamp"]),
        "nonce": _to_hex(transaction["nonce"]),
        "status": transaction_status,
        "from": _to_hex(transaction["from"]),
        "to": _to_hex(transaction["to"]),
        "value": _to_hex(transaction["value"]),
        "transaction_fee": _to_hex(
            transaction["gas"] * transaction["gasPrice"]
            if transaction["gas"] and transaction["gasPrice"]
            else 0
        ),
        "gas": _to_hex(transaction["gas"]),
        "gas_price": _to_hex(receipt["effectiveGasPrice"]),
        "input": _to_hex(transaction["input"]),
        "v": _to_hex(transaction["v"]),
        "swap_details": apply_to_hex(swap_details),
    }

    return transaction_data


async def fetch_latests_transactions_application(
    session: AsyncSession,
    limit: int = 10,
):
    latest_block = await async_web3.eth.get_block("latest")
    transactions = []

    limit = min(limit, len(latest_block["transactions"]))

    count = 0
    for tx_hash in latest_block["transactions"]:
        transaction = await get_transaction_by_hash_application(
            transaction_hash=tx_hash, session=session
        )

        if transaction is None:
            continue

        transactions.append(transaction)
        count += 1

        if count >= limit:
            break

    return transactions
