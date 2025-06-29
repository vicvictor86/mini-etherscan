from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class SandwichAttackGroup(Base):
    __tablename__ = "sandwich_attack_group"

    id = Column(Integer, primary_key=True, index=True)
    block_number = Column(String, index=True)
    ta1 = Column(String, nullable=False)
    tv = Column(String, nullable=False)
    ta2 = Column(String, nullable=False)

    attacks = relationship("SandwichAttack", back_populates="group")


class SandwichAttack(Base):
    __tablename__ = "sandwiches_attacks"

    id = Column(Integer, primary_key=True, index=True)
    attack_group_id = Column(Integer, ForeignKey("sandwich_attack_group.id"))
    block_number = Column(String, index=True)
    hash = Column(String, nullable=False)
    from_address = Column("from", String)
    to_address = Column("to", String)
    token_in = Column(String)
    token_out = Column(String)
    amount_in = Column(String)
    amount_out = Column(String)
    gas_price = Column(String)
    transition_type = Column(String)

    group = relationship("SandwichAttackGroup", back_populates="attacks")


class BlockAnalyzed(Base):
    __tablename__ = "blocks_analyzed"
    block_number = Column(String, primary_key=True, index=True)


class TransactionSwap(Base):
    __tablename__ = "transactions_swap"

    hash = Column(String, primary_key=True)
    block_number = Column(String, primary_key=True)
    log_index = Column(Integer, primary_key=True)
    transaction_index = Column(Integer)
    from_address = Column("from", String)
    to_address = Column("to", String)
    dex_name = Column(String)
    token_in = Column("tokenIn", String)
    token_in_address = Column("tokenInAddress", String)
    token_out = Column("tokenOut", String)
    token_out_address = Column("tokenOutAddress", String)
    amount_in = Column("amountIn", String)
    amount_out = Column("amountOut", String)
    gas_price = Column("gasPrice", String)
    gas_used = Column(Integer)
    gas_fee_wei = Column(String)
    gas_fee_eth = Column(String)
    gas_burned = Column(String, nullable=True)
    gas_tipped = Column(String, nullable=True)


class DexName(Base):
    __tablename__ = "dex_name"
    pool_address = Column(String, primary_key=True)
    dex_name = Column(String, nullable=False)
