from pydantic import BaseModel, Field
from typing import List, Optional


class SandwichAttackSchema(BaseModel):
    id: int
    attack_group_id: int
    block_number: int
    hash: str
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    token_in: Optional[str] = None
    token_out: Optional[str] = None
    amount_in: Optional[str] = None
    amount_out: Optional[str] = None
    gas_price: Optional[str] = None
    transition_type: Optional[str] = None

    class Config:
        from_attributes = True
        validate_by_name = True
        # quando gerar dict()/json(), use o alias como chave
        allow_population_by_alias = True


class SandwichAttackGroupSchema(BaseModel):
    id: int
    block_number: int
    ta1: str
    tv: str
    ta2: str
    attacks: List[SandwichAttackSchema] = []

    class Config:
        from_attributes = True
        validate_by_name = True
        # quando gerar dict()/json(), use o alias como chave
        allow_population_by_alias = True


class BlockAnalyzedSchema(BaseModel):
    block_number: int

    class Config:
        from_attributes = True
        validate_by_name = True
        # quando gerar dict()/json(), use o alias como chave
        allow_population_by_alias = True


class TransactionSwapSchema(BaseModel):
    hash: str
    block_number: int
    log_index: int
    transaction_index: Optional[int] = None
    from_address: Optional[str] = Field(None, alias="from")
    to_address: Optional[str] = Field(None, alias="to")
    dex_name: Optional[str] = None
    token_in: Optional[str] = Field(None, alias="tokenIn")
    token_in_address: Optional[str] = Field(None, alias="tokenInAddress")
    token_out: Optional[str] = Field(None, alias="tokenOut")
    token_out_address: Optional[str] = Field(None, alias="tokenOutAddress")
    amount_in: Optional[str] = Field(None, alias="amountIn")
    amount_out: Optional[str] = Field(None, alias="amountOut")
    gas_price: Optional[str] = Field(None, alias="gasPrice")
    gas_used: Optional[int] = Field(None, alias="gasUsed")
    gas_fee_wei: Optional[str] = Field(None, alias="gasFeeWei")
    gas_fee_eth: Optional[str] = Field(None, alias="gasFeeEth")
    gas_burned: Optional[str] = Field(None, alias="gasBurned")
    gas_tipped: Optional[str] = Field(None, alias="gasTipped")

    class Config:
        from_attributes = True
        validate_by_name = True
        # quando gerar dict()/json(), use o alias como chave
        allow_population_by_alias = True


class DexNameSchema(BaseModel):
    pool_address: str
    dex_name: str

    class Config:
        from_attributes = True
        validate_by_name = True
        # quando gerar dict()/json(), use o alias como chave
        allow_population_by_alias = True
