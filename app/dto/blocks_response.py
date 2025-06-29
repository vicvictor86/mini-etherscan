from typing import List
from pydantic import BaseModel


class Withdrawal(BaseModel):
    address: str
    amount: int
    index: int
    validatorIndex: int


class BlockItem(BaseModel):
    hash: str
    number: int
    nonce: str
    miner: str
    parent_hash: str
    timestamp: int
    status: str
    size: int
    gas_used: int
    base_fee_per_gas: int
    gas_limit: int
    difficulty: int
    total_difficulty: int
    withdrawals: List[Withdrawal]
    extra_data: str
    transactions_hashes: List[str]


class BlocksResponse(BaseModel):
    blocks: List[BlockItem]
