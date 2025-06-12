from fastapi import HTTPException
from hexbytes import HexBytes
from web3.exceptions import InvalidAddress
from web3 import Web3
import requests
import os

from app.application.web3_client.main import w3
from app.utils.loggers import error_logger

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BASE_URL = "https://api.etherscan.io/api"


def fetch_txs_from_etherscan_application(
    address: str,
    startblock: int = 0,
    endblock: int = 99999999,
    page: int = 1,
    per_page: int = 10,
):
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": startblock,
        "endblock": endblock,
        "page": page,
        "offset": per_page,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY,
    }
    resp = requests.get(BASE_URL, params=params)
    data = resp.json()
    print(data)
    if data["status"] != "1":
        if data["result"] == "Error! Invalid address format":
            raise HTTPException(status_code=400, detail="Endereço Ethereum inválido")

        error_logger.error(f"Erro Etherscan: {data}")
        raise RuntimeError(data.get("message", "Erro Etherscan"))
    return data["result"]


def get_address_application(address: str) -> dict:
    try:
        checksum_addr = w3.to_checksum_address(address)
    except (InvalidAddress, ValueError):
        raise HTTPException(status_code=400, detail="Endereço Ethereum inválido")

    try:
        balance_wei = w3.eth.get_balance(checksum_addr)
        tx_count = w3.eth.get_transaction_count(checksum_addr)
        code = w3.eth.get_code(checksum_addr)
    except Exception as e:
        error_logger.error(f"Erro ao consultar endereço {address}: {e}")
        raise HTTPException(status_code=502, detail="Erro ao consultar a blockchain")

    return {
        "address": checksum_addr,
        "is_contract": not (isinstance(code, (bytes, HexBytes)) and len(code) == 0),
        "balance_wei": balance_wei,
        "balance_eth": str(Web3.from_wei(balance_wei, "ether")),
        "transaction_count": tx_count,
    }
