from web3 import Web3, AsyncWeb3
import os

INFURA_URL = f"https://mainnet.infura.io/v3/{os.getenv('API_KEY')}"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))
async_web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(INFURA_URL))
