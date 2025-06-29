from typing import List, Literal
from pydantic import BaseModel


class Swap(BaseModel):
    hash: str
    from_address: str
    to_address: str
    token_in: str
    token_out: str
    amount_in: str
    amount_out: str
    gas_price: str
    transition_type: Literal["attacker", "victim"]


class SandwichItem(BaseModel):
    attack_group_id: int
    block_number: str
    ta1: str
    tv: str
    ta2: str
    swaps: List[Swap]


class SingleSandwichResponse(BaseModel):
    block_number: int
    sandwiches: List[SandwichItem]
    total_sandwiches: int
