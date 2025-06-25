from typing import List, Dict
import aiosqlite
from fastapi import Request

DB_FILE = "sandwiches_attacks.db"


async def create_connection(db_file: str = DB_FILE) -> aiosqlite.Connection:
    """
    Cria uma conexão assíncrona com o banco de dados SQLite.
    """
    conn = await aiosqlite.connect(db_file)
    # Habilita retorno de dicionários
    conn.row_factory = aiosqlite.Row
    return conn


async def create_tables() -> None:
    """
    Cria as tabelas sandwiches_attacks e sandwich_attack_group caso não existam.
    """
    conn = await create_connection()
    try:
        # Tabela de grupos de ataque (sandwich)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sandwich_attack_group (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_number TEXT,
                ta1 TEXT,
                tv TEXT,
                ta2 TEXT
            )
        """
        )
        # Tabela de ataques individuais
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sandwiches_attacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attack_group_id INTEGER,
            block_number TEXT,
            hash TEXT,
            "from" TEXT,
            "to" TEXT,
            token_in TEXT,
            token_out TEXT,
            amount_in TEXT,
            amount_out TEXT,
            gas_price TEXT,
            transition_type TEXT,
            FOREIGN KEY (attack_group_id) REFERENCES sandwich_attack_group(id)
            )
        """
        )
        # Tabela para registrar blocos analisados
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blocks_analyzed (
                block_number TEXT PRIMARY KEY
            )
        """
        )
        # Tabela para registrar transações únicas
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions_swap (
                hash TEXT PRIMARY KEY,
                block_number TEXT,
                transaction_index INTEGER,
                "from" TEXT,
                "to" TEXT,
                dex_name TEXT,
                tokenIn TEXT,
                tokenOut TEXT,
                amountIn TEXT,
                amountOut TEXT,
                gasPrice TEXT
            )
            """
        )
        # Tabela para registrar o nome da DEX associado ao endereço do pool
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dex_name (
                pool_address TEXT PRIMARY KEY,
                dex_name TEXT
            )
            """
        )
        await conn.commit()
    finally:
        await conn.close()


async def insert_dex_name(
    request: Request,
    pool_address: str,
    dex_name: str,
) -> None:
    """
    Insere o nome da DEX associado ao endereço do pool de forma assíncrona.
    """
    conn = request.app.state.db
    try:
        await conn.execute(
            """
            INSERT INTO dex_name (pool_address, dex_name) VALUES (?, ?)
        """,
            (pool_address, dex_name),
        )
        await conn.commit()
    except aiosqlite.IntegrityError:
        # Ignora se o endereço do pool já foi inserido
        pass


async def get_dex_name_by_pool_address(
    request: Request,
    pool_address: str,
) -> str:
    """
    Retorna o nome da DEX associado ao endereço do pool de forma assíncrona.
    """
    conn = request.app.state.db
    cursor = await conn.execute(
        """
        SELECT dex_name FROM dex_name WHERE pool_address = ?
    """,
        (pool_address,),
    )
    row = await cursor.fetchone()
    if row:
        return row["dex_name"]
    return None


async def insert_transaction_swap(
    request: Request,
    swap_data: Dict,
) -> None:
    """
    Insere um registro na tabela transactions_swap de forma assíncrona.
    """
    conn = request.app.state.db
    try:
        await conn.execute(
            """
            INSERT INTO transactions_swap (
                hash, block_number, transaction_index, "from", "to", dex_name, tokenIn, tokenOut, amountIn, amountOut, gasPrice
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                swap_data["hash"],
                swap_data["block_number"],
                swap_data["transaction_index"],
                swap_data["from"],
                swap_data["to"],
                swap_data.get("dex_name", ""),
                swap_data["tokenIn"],
                swap_data["tokenOut"],
                swap_data["amountIn"],
                swap_data["amountOut"],
                swap_data["gasPrice"],
            ),
        )
        await conn.commit()
    except aiosqlite.IntegrityError:
        # Ignora se a transação já foi inserida
        pass


async def get_transaction_swap_by_hash(request: Request, hash_value: str) -> Dict:
    """Retorna um registro da tabela transactions_swap filtrado pelo hash de forma assíncrona."""
    conn = request.app.state.db
    cursor = await conn.execute(
        """
        SELECT * FROM transactions_swap WHERE hash = ?
    """,
        (hash_value,),
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)
    return None


async def insert_block_analyzed(request: Request, block_number: str) -> None:
    """
    Insere um registro na tabela blocks_analyzed de forma assíncrona.
    """
    conn = request.app.state.db
    try:
        await conn.execute(
            """
            INSERT INTO blocks_analyzed (block_number) VALUES (?)
        """,
            (block_number,),
        )
        await conn.commit()
    except aiosqlite.IntegrityError:
        # Ignora se o bloco já foi inserido
        pass


async def get_analyzed_blocks_by_block_number(request: Request, block_number: int):
    """
    Retorna um registro da tabela blocks_analyzed filtrado pelo block_number de forma assíncrona.
    """
    conn = request.app.state.db
    cursor = await conn.execute(
        """
        SELECT block_number FROM blocks_analyzed WHERE block_number = ?
    """,
        (block_number,),
    )
    row = await cursor.fetchone()
    return row is not None


async def insert_attack(
    request: Request,
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
    """
    Insere um registro na tabela sandwiches_attacks de forma assíncrona.
    """
    conn = request.app.state.db
    await conn.execute(
        """
        INSERT INTO sandwiches_attacks (
            attack_group_id, block_number, hash, "from", "to", token_in, token_out,
            amount_in, amount_out, gas_price, transition_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            attack_group_id,
            block_number,
            hash_value,
            from_address,
            to_address,
            token_in,
            token_out,
            amount_in,
            amount_out,
            gas_price,
            transition_type,
        ),
    )
    await conn.commit()


async def get_attacks_by_block_number(
    request: Request, block_number: str
) -> List[Dict]:
    """
    Retorna todos os registros da tabela filtrados pelo block_number de forma assíncrona.
    """
    conn = request.app.state.db
    cursor = await conn.execute(
        """
        SELECT
            block_number,
            hash,
            "from",
            "to",
            token_in,
            token_out,
            amount_in,
            amount_out,
            gas_price,
            transition_type
        FROM sandwiches_attacks
        WHERE block_number = ?
    """,
        (block_number,),
    )
    rows = await cursor.fetchall()

    result: List[Dict] = [dict(row) for row in rows]
    return result


async def insert_attack_group(
    request: Request,
    block_number: str,
    ta1: str,
    tv: str,
    ta2: str,
) -> int:
    """
    Insere um grupo de ataque (sandwich) na tabela sandwich_attack_group e
    devolve o ID gerado (AUTOINCREMENT).
    """
    conn = request.app.state.db

    cursor = await conn.execute(
        """
        INSERT INTO sandwich_attack_group (
            block_number, ta1, tv, ta2
        ) VALUES (?, ?, ?, ?)
        """,
        (block_number, ta1, tv, ta2),
    )

    await conn.commit()

    return cursor.lastrowid


async def get_attack_groups_by_block(request: Request, block_number: str) -> List[Dict]:
    """
    Retorna todos os grupos de ataque associados a um block_number.
    """
    conn = request.app.state.db
    cursor = await conn.execute(
        """
        SELECT * FROM sandwich_attack_group WHERE block_number = ?
    """,
        (block_number,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_sandwich_attacks_by_block_grouped_by_attack_group(
    request: Request,
    block_number: str,
) -> List[Dict]:
    """
    Retorna todos os ataques de sandwich agrupados por attack_group_id para um block_number específico.
    """
    conn = request.app.state.db
    cursor = await conn.execute(
        """
        SELECT
            sa.attack_group_id,
            sa.block_number,
            sa.hash,
            sa."from" AS from_address,
            sa."to" AS to_address,
            sa.token_in,
            sa.token_out,
            sa.amount_in,
            sa.amount_out,
            sa.gas_price,
            sa.transition_type,
            ag.ta1,
            ag.tv,
            ag.ta2
        FROM sandwiches_attacks AS sa
        JOIN sandwich_attack_group AS ag ON sa.attack_group_id = ag.id
        WHERE sa.block_number = ?
    """,
        (block_number,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def save_detected_sandwich(
    request: Request, block: Dict, ta1: Dict, tv: Dict, ta2: Dict
) -> None:
    """
    Insere no banco as três transações do sandwich e o grupo correspondente.
    """
    # Insere o grupo de sandwich (ta1, tv, ta2)
    attack_group_id = await insert_attack_group(
        request=request,
        block_number=str(block["number"]),
        ta1=ta1["hash"],
        tv=tv["hash"],
        ta2=ta2["hash"],
    )

    # Insere cada transação individualmente
    await insert_attack(
        request=request,
        attack_group_id=attack_group_id,
        block_number=str(block["number"]),
        hash_value=ta1["hash"],
        from_address=ta1["from"],
        to_address=ta1["to"],
        token_in=ta1["tokenIn"],
        token_out=ta1["tokenOut"],
        amount_in=str(ta1["amountIn"]),
        amount_out=str(ta1["amountOut"]),
        gas_price=str(ta1["gasPrice"]),
        transition_type="attacker",
    )
    await insert_attack(
        request=request,
        attack_group_id=attack_group_id,
        block_number=str(block["number"]),
        hash_value=tv["hash"],
        from_address=tv["from"],
        to_address=tv["to"],
        token_in=tv["tokenIn"],
        token_out=tv["tokenOut"],
        amount_in=str(tv["amountIn"]),
        amount_out=str(tv["amountOut"]),
        gas_price=str(tv["gasPrice"]),
        transition_type="victim",
    )
    await insert_attack(
        request=request,
        attack_group_id=attack_group_id,
        block_number=str(block["number"]),
        hash_value=ta2["hash"],
        from_address=ta2["from"],
        to_address=ta2["to"],
        token_in=ta2["tokenIn"],
        token_out=ta2["tokenOut"],
        amount_in=str(ta2["amountIn"]),
        amount_out=str(ta2["amountOut"]),
        gas_price=str(ta2["gasPrice"]),
        transition_type="attacker",
    )
