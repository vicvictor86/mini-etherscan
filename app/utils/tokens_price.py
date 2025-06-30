from app.application.web3_client.main import async_web3
import httpx
import os


async def get_binance_price(symbol: str):
    if symbol == "USDT":
        return 1.0
    if symbol == "WETH":
        symbol = "ETH"

    url = f"{os.getenv("BINANCE_BASE_URL")}/api/v3/ticker/price?symbol={symbol}USDT"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return float(data["price"])
    except Exception as e:
        print(f"Erro buscando preço de {symbol}: {e}")
        return None


async def get_token_decimals(token_address):
    contract = async_web3.eth.contract(
        address=token_address,
        abi=[
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function",
            }
        ],
    )
    return await contract.functions.decimals().call()
