from pydantic import BaseModel, Field
from typing import Optional


class SwapDetails(BaseModel):
    hash: str
    block_number: int
    log_index: int
    transaction_index: int
    from_: str = Field(..., alias="from")
    to: str
    tokenIn: str = Field(..., alias="token_in")
    tokenOut: str = Field(..., alias="token_out")
    amountIn: str = Field(..., alias="amount_in")
    amountOut: str = Field(..., alias="amount_out")
    gasPrice: str = Field(..., alias="gas_price")
    dex_name: str

    class Config:
        validate_by_name = True
        from_attributes = True


class TransactionResponse(BaseModel):
    transaction_hash: str
    transaction_index: int
    block_hash: str
    block_number: int
    timestamp: int
    nonce: int
    status: str
    from_: str = Field(..., alias="from")
    to: str
    value: int
    transaction_fee: int
    gas: int
    gas_price: int
    input: str
    v: int
    swap_details: Optional[SwapDetails]

    class Config:
        validate_by_name = True
