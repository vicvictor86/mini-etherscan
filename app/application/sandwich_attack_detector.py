import os
from eth_utils import event_abi_to_log_topic
from eth_abi import decode
from fastapi import Request
from web3._utils.events import get_event_data
from web3 import AsyncWeb3
import httpx
import json

from app.dbo.sandwiches_attacks_db import save_detected_sandwich

UNISWAP_V2_SWAP_ABI = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "sender", "type": "address"},
        {"indexed": False, "name": "amount0In", "type": "uint256"},
        {"indexed": False, "name": "amount1In", "type": "uint256"},
        {"indexed": False, "name": "amount0Out", "type": "uint256"},
        {"indexed": False, "name": "amount1Out", "type": "uint256"},
        {"indexed": True, "name": "to", "type": "address"},
    ],
    "name": "Swap",
    "type": "event",
}

UNISWAP_V3_SWAP_ABI = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "sender", "type": "address"},
        {"indexed": True, "name": "recipient", "type": "address"},
        {"indexed": False, "name": "amount0", "type": "int256"},
        {"indexed": False, "name": "amount1", "type": "int256"},
        {"indexed": False, "name": "sqrtPriceX96", "type": "uint160"},
        {"indexed": False, "name": "liquidity", "type": "uint128"},
        {"indexed": False, "name": "tick", "type": "int24"},
    ],
    "name": "Swap",
    "type": "event",
}

SWAP_V2_TOPIC = event_abi_to_log_topic(UNISWAP_V2_SWAP_ABI)
SWAP_V3_TOPIC = event_abi_to_log_topic(UNISWAP_V3_SWAP_ABI)

PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
]

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
]


async def fetch_pair_abi(address: str) -> list[dict]:
    url = (
        "https://api.etherscan.io/api"
        f"?module=contract&action=getabi&address={address}"
        f"&apikey={os.getenv('ETHERSCAN_API_KEY', '')}"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()

    if data["status"] != "1":
        raise RuntimeError(f"Erro ao buscar ABI: {data.get('result')}")

    abi = json.loads(data["result"])
    return abi


# TODO: Puxar o swap details em ABIs diferente de Uniswap V2 e V3
async def get_swap_details(async_web3: AsyncWeb3, tx_hash):
    tx = await async_web3.eth.get_transaction(tx_hash)
    receipt = await async_web3.eth.get_transaction_receipt(tx_hash)

    for log in receipt.logs:
        topic0 = log.topics[0]
        pool_addr = async_web3.to_checksum_address(log.address)

        # Uniswap V2 / Sushiswap
        if topic0 == SWAP_V2_TOPIC:
            # decodifica amount0In, amount1In, amount0Out, amount1Out
            a0in, a1in, a0out, a1out = decode(
                ["uint256", "uint256", "uint256", "uint256"], log.data
            )

            pair = async_web3.eth.contract(address=log.address, abi=PAIR_ABI)
            addr0 = await pair.functions.token0().call()
            addr1 = await pair.functions.token1().call()

            # busca símbolos ERC-20
            token0_contract = async_web3.eth.contract(address=addr0, abi=ERC20_ABI)
            token1_contract = async_web3.eth.contract(address=addr1, abi=ERC20_ABI)
            try:
                sym0 = await token0_contract.functions.symbol().call()
            except:
                sym0 = addr0
            try:
                sym1 = await token1_contract.functions.symbol().call()
            except:
                sym1 = addr1

            # define tokenIn/tokenOut e quantidades
            if a0in > 0:
                token_in, token_out = sym0, sym1
                amount_in, amount_out = a0in, a1out
            else:
                token_in, token_out = sym1, sym0
                amount_in, amount_out = a1in, a0out

        # Uniswap V3
        elif topic0 == SWAP_V3_TOPIC:
            # decodifica amount0, amount1, sqrtPriceX96, liquidity, tick
            amt0, amt1, _, _, _ = decode(
                ["int256", "int256", "uint160", "uint128", "int24"], log.data
            )

            # resolve endereço de token0/token1 no pool
            pair = async_web3.eth.contract(address=log.address, abi=PAIR_ABI)
            addr0 = await pair.functions.token0().call()
            addr1 = await pair.functions.token1().call()

            # busca símbolos ERC-20
            token0_contract = async_web3.eth.contract(address=addr0, abi=ERC20_ABI)
            token1_contract = async_web3.eth.contract(address=addr1, abi=ERC20_ABI)
            try:
                sym0 = await token0_contract.functions.symbol().call()
            except:
                sym0 = addr0
            try:
                sym1 = await token1_contract.functions.symbol().call()
            except:
                sym1 = addr1

            if amt0 > 0:
                token_in, token_out = sym0, sym1
                amount_in, amount_out = amt0, abs(amt1)
            else:
                token_in, token_out = sym1, sym0
                amount_in, amount_out = amt1, abs(amt0)

        else:
            continue
            # try:
            #     # 3.1 busca ABI do par
            #     pair_abi = await fetch_pair_abi(pool_addr)
            # except RuntimeError:
            #     continue  # pula se não encontrar ABI

            # # 3.2 encontra o event_abi que bate com topic0
            # event_abi = next(
            #     (
            #         e
            #         for e in pair_abi
            #         if e.get("type") == "event" and event_abi_to_log_topic(e) == topic0
            #     ),
            #     None,
            # )
            # if event_abi is None:
            #     continue

            # # 3.3 decodifica todos os args
            # decoded = get_event_data(async_web3.codec, event_abi, log)
            # args = decoded["args"]

            # # 3.4 extrai non-indexed numéricos como amountIn/Out
            # non_idx = [inp for inp in event_abi["inputs"] if not inp["indexed"]]
            # nums = [
            #     args[inp["name"]]
            #     for inp in non_idx
            #     if inp["type"].startswith(("uint", "int"))
            # ]
            # amount_in = nums[0] if len(nums) > 0 else None
            # amount_out = nums[1] if len(nums) > 1 else None

            # # 3.5 extrai indexed address como tokenIn/Out
            # idx_addr = [
            #     inp
            #     for inp in event_abi["inputs"]
            #     if inp["indexed"] and inp["type"] == "address"
            # ]
            # token_in = ("0x" + log.topics[1].hex()[-40:]) if len(idx_addr) > 0 else None
            # token_out = (
            #     ("0x" + log.topics[2].hex()[-40:]) if len(idx_addr) > 1 else None
            # )

            # return {
            #     "hash": tx_hash,
            #     "from": tx["from"],
            #     "to": pool_addr,
            #     "tokenIn": token_in,
            #     "tokenOut": token_out,
            #     "amountIn": str(amount_in) if amount_in is not None else None,
            #     "amountOut": str(amount_out) if amount_out is not None else None,
            #     "gasPrice": str(tx["gasPrice"]),
            # }

        to_addr = "0x" + log.topics[2].hex()[-40:]

        print(f"Swap collected: {tx_hash}")

        return {
            "hash": tx_hash,
            "from": tx["from"],
            "to": pool_addr,
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountIn": str(amount_in),
            "amountOut": str(amount_out),
            "gasPrice": str(tx["gasPrice"]),
        }

    # se não encontrou nenhum Swap
    return None


async def detect_sandwiches(request: Request, block, amount_tol=0.01):
    txs = block["transactions"]
    detected = []
    n = len(txs)

    for j in range(n):
        tv = txs[j]
        target = tv["tokenOut"]
        dex = tv["to"]
        gas_tv = float(tv["gasPrice"])

        for i in range(n):
            if i == j:
                continue

            ta1 = txs[i]

            if ta1["from"] == tv["from"]:
                continue

            if ta1["tokenOut"] != target or ta1["to"] != dex:
                continue

            # if float(ta1["gasPrice"]) <= gas_tv:
            #     continue

            for k in range(n):
                if k == i or k == j:
                    continue

                ta2 = txs[k]

                if ta2["from"] != ta1["from"]:
                    continue
                if ta2["tokenIn"] != target or ta2["to"] != dex:
                    continue
                # if float(ta2["gasPrice"]) >= gas_tv:
                #     continue
                # if (
                #     abs(float(ta1["amountOut"]) - float(ta2["amountIn"]))
                #     / float(ta1["amountOut"])
                #     > amount_tol
                # ):
                #     continue

                await save_detected_sandwich(request, block, ta1, tv, ta2)
                detected.append(
                    {
                        "block": block["number"],
                        "ta1": ta1["hash"],
                        "tv": tv["hash"],
                        "ta2": ta2["hash"],
                    }
                )
    return detected
