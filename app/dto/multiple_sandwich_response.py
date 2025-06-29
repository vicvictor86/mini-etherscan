from typing import List, Dict, Union, Optional
from pydantic import BaseModel, Field


class SwapEvent(BaseModel):
    to_address: str
    amount_out: str
    gas_fee_wei: str
    gas_price: str
    gas_fee_eth: str
    hash: str
    from_address: str
    gas_burned: str
    block_number: str
    token_in: str
    gas_tipped: str
    log_index: int
    token_in_address: str
    transaction_index: int
    token_out: str
    dex_name: str
    token_out_address: str
    amount_in: str
    gas_used: int


class Swaps(BaseModel):
    front_run: List[SwapEvent]
    victims: List[SwapEvent]
    back_run: List[SwapEvent]


class SandwichAttack(BaseModel):
    block: int
    attacker_addr: str
    victims_addr: List[str]
    cost_amount: float
    gain_amount: float
    cost_usd: float
    gain_usd: float
    swaps: Swaps


class MultipleSandwichResponse(BaseModel):
    block_number: int
    sandwiches: List[SandwichAttack]
    total_sandwiches: int


# Exemplo de uso:
# resp = SandwichesResponse(**your_json_dict)
