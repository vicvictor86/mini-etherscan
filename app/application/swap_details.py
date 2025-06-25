from fastapi import Request
from web3._utils.events import get_event_data
from eth_utils import event_abi_to_log_topic
from eth_abi import decode
from web3 import AsyncWeb3
import httpx
import json
import os
import asyncio

from app.utils.get_dex_name import get_dex_name

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


async def is_swap_event(async_web3, log):
    # Busca ABI do contrato do log.address
    try:
        abi = await fetch_pair_abi(log.address)
    except Exception:
        return None, None  # Não achou ABI

    for event in abi:
        if event.get("type") == "event":
            # Pode customizar aqui: nome igual a "Swap" ou mais heurísticas
            print(f"Checking event: {event['name']} in {log.address}")
            if event["name"].lower() == "swap":
                swap_topic = event_abi_to_log_topic(event)
                if swap_topic == log.topics[0]:
                    # É Swap, retorna o event_abi
                    print(f"Swap event found: {event['name']} in {log.address}")
                    return event, abi
    return None, abi


async def get_swap_details_web3_etherscan(async_web3: AsyncWeb3, tx_hash):
    tx = await async_web3.eth.get_transaction(tx_hash)
    receipt = await async_web3.eth.get_transaction_receipt(tx_hash)

    for log in receipt.logs:
        swap_event_abi, contract_abi = await is_swap_event(async_web3, log)
        if not swap_event_abi:
            continue  # Não é swap, pula

        pool_addr = async_web3.to_checksum_address(log.address)
        # # Busca ABI do contrato da pool/pair/pool/whatever
        # try:
        #     pair_abi = await fetch_pair_abi(pool_addr)
        # except RuntimeError as e:
        #     continue  # se não conseguir buscar, pula

        # Procura o event_abi que bate com o topic0 do log
        # event_abi = next(
        #     (
        #         e
        #         for e in pair_abi
        #         if e.get("type") == "event"
        #         and event_abi_to_log_topic(e) == log.topics[0]
        #     ),
        #     None,
        # )
        # if event_abi is None:
        #     continue  # Não encontrou evento compatível

        # Decodifica o evento do log
        try:
            decoded = get_event_data(async_web3.codec, swap_event_abi, log)
            args = decoded["args"]
        except Exception as e:
            continue

        # Pega campos numéricos (amounts) e de endereço
        non_indexed = [inp for inp in swap_event_abi["inputs"] if not inp["indexed"]]
        indexed = [inp for inp in swap_event_abi["inputs"] if inp["indexed"]]

        # Extrai os amounts
        nums = [
            args[inp["name"]]
            for inp in non_indexed
            if inp["type"].startswith(("uint", "int"))
        ]
        amount_in = nums[0] if len(nums) > 0 else None
        amount_out = nums[1] if len(nums) > 1 else None

        # Extrai os endereços indexados como tokenIn/Out (heurística genérica)
        addresses = [args[inp["name"]] for inp in indexed if inp["type"] == "address"]
        token_in = addresses[0] if len(addresses) > 0 else None
        token_out = addresses[1] if len(addresses) > 1 else None

        # Busca símbolo do token, se possível
        async def resolve_symbol(addr):
            if addr is None:
                return None
            contract = async_web3.eth.contract(address=addr, abi=ERC20_ABI)
            try:
                return await contract.functions.symbol().call()
            except Exception:
                return addr  # fallback: mostra address

        sym_token_in = await resolve_symbol(token_in)
        sym_token_out = await resolve_symbol(token_out)

        # Pegando para quem foi (opcional, heurística: usa topic[2] se existir)
        to_addr = ("0x" + log.topics[2].hex()[-40:]) if len(log.topics) > 2 else None

        print(f"Swap collected: {tx_hash} ({sym_token_in} -> {sym_token_out})")

        return {
            "hash": tx_hash,
            "from": tx["from"],
            "to": pool_addr,
            "tokenIn": sym_token_in,
            "tokenOut": sym_token_out,
            "amountIn": str(amount_in) if amount_in is not None else None,
            "amountOut": str(amount_out) if amount_out is not None else None,
            "gasPrice": str(tx["gasPrice"]),
        }

    # se não encontrou nenhum swap genérico
    return None


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


# TODO: Puxar o swap details em ABIs diferente de Uniswap V2 e V3
async def get_swap_details_web3(
    async_web3: AsyncWeb3, tx_hash, request: Request | None = None
):
    tx_task = asyncio.create_task(async_web3.eth.get_transaction(tx_hash))
    receipt_task = asyncio.create_task(async_web3.eth.get_transaction_receipt(tx_hash))
    tx, receipt = await asyncio.gather(tx_task, receipt_task)

    for log in receipt.logs:
        if len(log.topics) == 0:
            continue
        topic0 = log.topics[0]
        pool_addr = async_web3.to_checksum_address(log.address)

        # Uniswap V2 / Sushiswap
        if topic0 == SWAP_V2_TOPIC:
            # decodifica amount0In, amount1In, amount0Out, amount1Out
            a0in, a1in, a0out, a1out = decode(
                ["uint256", "uint256", "uint256", "uint256"], log.data
            )

            pair = async_web3.eth.contract(address=log.address, abi=PAIR_ABI)
            addr0_task = asyncio.create_task(pair.functions.token0().call())
            addr1_task = asyncio.create_task(pair.functions.token1().call())
            addr0, addr1 = await asyncio.gather(addr0_task, addr1_task)

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
            addr0_task = asyncio.create_task(pair.functions.token0().call())
            addr1_task = asyncio.create_task(pair.functions.token1().call())
            addr0, addr1 = await asyncio.gather(addr0_task, addr1_task)

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

        dex_name = await get_dex_name(pool_address=pool_addr, request=request)

        to_addr = "0x" + log.topics[2].hex()[-40:]

        print(f"Swap collected: {tx_hash}")

        return {
            "hash": tx_hash,
            "block_number": tx["blockNumber"],
            "transaction_index": tx["transactionIndex"],
            "from": tx["from"],
            "to": pool_addr,
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountIn": str(amount_in),
            "amountOut": str(amount_out),
            "gasPrice": str(tx["gasPrice"]),
            "dex_name": dex_name,
        }

    # se não encontrou nenhum Swap
    return None
