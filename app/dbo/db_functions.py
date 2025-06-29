from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.dbo.models import (
    DexName,
    TransactionSwap,
    BlockAnalyzed,
    SandwichAttack,
    SandwichAttackGroup,
)


# — DexName —
async def insert_dex_name(
    session: AsyncSession, pool_address: str, dex_name: str
) -> None:
    obj = DexName(pool_address=pool_address, dex_name=dex_name)
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()  # já existe, ignora


async def get_dex_name_by_pool_address(
    session: AsyncSession, pool_address: str
) -> str | None:
    with session.no_autoflush:
        res = await session.get(DexName, pool_address)

    return res.dex_name if res else None


# — TransactionSwap —
async def insert_transaction_swap(session: AsyncSession, swap_data: dict) -> None:
    obj = TransactionSwap(
        hash=swap_data["hash"],
        block_number=swap_data["block_number"],
        log_index=swap_data["log_index"],
        transaction_index=swap_data["transaction_index"],
        from_address=swap_data["from"],
        to_address=swap_data["to"],
        dex_name=swap_data.get("dex_name", ""),
        token_in=swap_data["tokenIn"],
        token_in_address=swap_data.get("tokenInAddress", ""),
        token_out=swap_data["tokenOut"],
        token_out_address=swap_data.get("tokenOutAddress", ""),
        amount_in=swap_data["amountIn"],
        amount_out=swap_data["amountOut"],
        gas_price=swap_data["gasPrice"],
        gas_used=swap_data.get("gasUsed", 0),
        gas_fee_wei=swap_data.get("gasFeeWei", "0"),
        gas_fee_eth=swap_data.get("gasFeeEth", "0"),
        gas_burned=swap_data.get("gasBurned", "0"),  # Gas burned
        gas_tipped=swap_data.get("gasTipped", "0"),  # Gas tipped
    )
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()  # ignora duplicatas


async def get_transaction_swap_by_hash(
    session: AsyncSession, hash_value: str
) -> TransactionSwap | None:
    q = await session.execute(
        select(TransactionSwap).where(TransactionSwap.hash == hash_value)
    )
    return q.scalars().first()


async def fetch_transactions_swap_by_hash(
    session: AsyncSession, hash_value: str
) -> list[TransactionSwap]:
    with session.no_autoflush:
        result = await session.execute(
            select(TransactionSwap).where(TransactionSwap.hash == hash_value)
        )
    return result.scalars().all()


async def fetch_transactions_swap_by_block_number(
    session: AsyncSession, block_number: str
) -> list[TransactionSwap]:
    with session.no_autoflush:
        result = await session.execute(
            select(TransactionSwap)
            .where(TransactionSwap.block_number == block_number)
            .order_by(TransactionSwap.transaction_index, TransactionSwap.log_index)
        )
    return result.scalars().all()


# — BlockAnalyzed —
async def insert_block_analyzed(session: AsyncSession, block_number: str) -> None:
    obj = BlockAnalyzed(block_number=block_number)
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()


async def get_analyzed_blocks_by_block_number(
    session: AsyncSession, block_number: str
) -> bool:
    res = await session.get(BlockAnalyzed, block_number)
    return res is not None


# — SandwichAttackGroup & SandwichAttack —
async def insert_attack_group(
    session: AsyncSession, block_number: str, ta1: str, tv: str, ta2: str
) -> int:
    group = SandwichAttackGroup(block_number=block_number, ta1=ta1, tv=tv, ta2=ta2)
    session.add(group)
    await session.flush()
    return group.id


async def insert_attack(
    session: AsyncSession,
    attack_group_id: int,
    block_number: str,
    hash_value: str,
    from_address: str,
    to_address: str,
    token_in: str,
    token_out: str,
    amount_in: str,
    amount_out: str,
    gas_price: str,
    transition_type: str,
) -> None:
    atk = SandwichAttack(
        attack_group_id=attack_group_id,
        block_number=block_number,
        hash=hash_value,
        from_address=from_address,
        to_address=to_address,
        token_in=token_in,
        token_out=token_out,
        amount_in=amount_in,
        amount_out=amount_out,
        gas_price=gas_price,
        transition_type=transition_type,
    )
    session.add(atk)


async def get_attacks_by_block_number(
    session: AsyncSession, block_number: str
) -> list[SandwichAttack]:
    q = await session.execute(
        select(SandwichAttack).where(SandwichAttack.block_number == block_number)
    )
    return q.scalars().all()


async def get_attack_groups_by_block(
    session: AsyncSession, block_number: str
) -> list[SandwichAttackGroup]:
    q = await session.execute(
        select(SandwichAttackGroup).where(
            SandwichAttackGroup.block_number == block_number
        )
    )
    return q.scalars().all()


async def get_sandwich_attacks_by_block_grouped_by_attack_group(
    session: AsyncSession, block_number: str
) -> list[dict]:
    q = await session.execute(
        select(
            SandwichAttack.attack_group_id,
            SandwichAttack.block_number,
            SandwichAttack.hash,
            SandwichAttack.from_address.label("from_address"),
            SandwichAttack.to_address.label("to_address"),
            SandwichAttack.token_in,
            SandwichAttack.token_out,
            SandwichAttack.amount_in,
            SandwichAttack.amount_out,
            SandwichAttack.gas_price,
            SandwichAttack.transition_type,
            SandwichAttackGroup.ta1,
            SandwichAttackGroup.tv,
            SandwichAttackGroup.ta2,
        )
        .join(SandwichAttackGroup)
        .where(SandwichAttack.block_number == block_number)
    )
    return [row._mapping for row in q.all()]


async def save_detected_sandwich(
    session: AsyncSession, block: dict, ta1: dict, tv: dict, ta2: dict
) -> None:
    # abre uma transação única
    async with session.begin():
        group_id = await insert_attack_group(
            session, str(block["number"]), ta1["hash"], tv["hash"], ta2["hash"]
        )
        # insere as três txs
        for tx, ttype in ((ta1, "attacker"), (tv, "victim"), (ta2, "attacker")):
            session.add(
                SandwichAttack(
                    attack_group_id=group_id,
                    block_number=str(block["number"]),
                    hash=tx["hash"],
                    from_address=tx["from"],
                    to_address=tx["to"],
                    token_in=tx["tokenIn"],
                    token_out=tx["tokenOut"],
                    amount_in=str(tx["amountIn"]),
                    amount_out=str(tx["amountOut"]),
                    gas_price=str(tx["gasPrice"]),
                    transition_type=ttype,
                )
            )
