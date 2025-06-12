from hexbytes import HexBytes

from app.application.web3_client.main import w3


def _to_hex(value):
    """
    Converte HexBytes ou bytes em string hex com '0x...'
    Senao, retorna o valor original.
    """
    if isinstance(value, (HexBytes, bytes)):
        return value.hex()
    return value


def get_transaction_by_hash_application(transaction_hash: str):
    transaction = w3.eth.get_transaction(transaction_hash=transaction_hash)

    print(transaction)

    receipt = w3.eth.get_transaction_receipt(transaction_hash)

    block = w3.eth.get_block(transaction["blockNumber"])

    print(receipt)
    transaction_status = "Success" if receipt["status"] == 1 else "Failed"

    transaction_data = {
        "transaction_hash": _to_hex(transaction["hash"]),
        "transaction_index": transaction["transactionIndex"],
        "block_hash": (
            _to_hex(transaction["blockHash"]) if transaction["blockHash"] else None
        ),
        "block_number": transaction["blockNumber"],
        "timestamp": block["timestamp"],
        "nonce": transaction["nonce"],
        "status": transaction_status,
        "from": transaction["from"],
        "to": transaction["to"],
        "value": transaction["value"],
        "transaction_fee": transaction["gas"] * transaction["gasPrice"] or 0,
        "gas": transaction["gas"],
        "gas_price": receipt["effectiveGasPrice"],
        "input": _to_hex(transaction["input"]),
        "v": _to_hex(transaction["v"]),
    }

    return transaction_data
