from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import os

from app.dbo.db_functions import get_dex_name_by_pool_address, insert_dex_name


async def get_dex_name(pool_address, session: AsyncSession | None = None):
    dex_name = await get_dex_name_by_pool_address(
        pool_address=pool_address,
        session=session,
    )

    if dex_name:
        return dex_name

    url = (
        f"https://api.etherscan.io/api"
        f"?module=contract&action=getsourcecode"
        f"&address={pool_address}"
        f"&apikey={os.getenv('ETHERSCAN_API_KEY')}"
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        data = response.json()

    if data.get("status") != "1" or not data.get("result"):
        return None

    contract_name = data["result"][0].get("ContractName", "")
    dex_map = {
        "UniswapV2Pair": "Uniswap V2",
        "UniswapV2PairV8": "Uniswap V2",
        "UniswapV3Pool": "Uniswap V3",
        "SushiSwapPair": "SushiSwap",
        "SushiV2Pair": "SushiSwap",
        "SushiPair": "SushiSwap",
    }
    dex_name = dex_map.get(contract_name, contract_name or "Unknown")

    await insert_dex_name(
        session=session,
        pool_address=pool_address,
        dex_name=dex_name,
    )
    return dex_name if dex_name else None
