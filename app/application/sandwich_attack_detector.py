from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dbo.db_functions import (
    save_detected_sandwich,
)
from app.dto.schemas import TransactionSwapSchema
from app.utils.tokens_price import get_binance_price, get_token_decimals
from collections import defaultdict


# TODO: Usar o mesmo método do multiple que parece está encontrando mais
async def detect_single_dex_sandwiches(session: AsyncSession, block, amount_tol=0.01):
    txs = block["transactions"]
    detected = []
    n = len(txs)

    for j in range(n):
        tv = txs[j]
        target = tv["tokenOut"]
        dex = tv["to"]
        gas_tv = float(tv["gasPrice"])

        for i in range(n):
            if i == j:
                continue

            ta1 = txs[i]

            if ta1["from"] == tv["from"]:
                continue

            if ta1["tokenOut"] != target or ta1["to"] != dex:
                continue

            # if float(ta1["gasPrice"]) <= gas_tv:
            #     continue

            for k in range(n):
                if k == i or k == j:
                    continue

                ta2 = txs[k]

                if ta2["from"] != ta1["from"]:
                    continue
                if ta2["tokenIn"] != target or ta2["to"] != dex:
                    continue
                # if float(ta2["gasPrice"]) >= gas_tv:
                #     continue
                # if (
                #     abs(float(ta1["amount_out"]) - float(ta2["amount_in"]))
                #     / float(ta1["amount_out"])
                #     > amount_tol
                # ):
                #     continue

                await save_detected_sandwich(session, block, ta1, tv, ta2)
                detected.append(
                    {
                        "block": block["number"],
                        "ta1": ta1["hash"],
                        "tv": tv["hash"],
                        "ta2": ta2["hash"],
                    }
                )
    return detected


async def detect_multi_layered_burger_sandwiches(
    session: AsyncSession,
    block,
    amount_tol=0.01,
    base_fee_per_gas=0,
):
    tokens_price = {}
    tokens_decimals = {}

    if "ETH" not in tokens_price:
        tokens_price["ETH"] = await get_binance_price("ETH")
    eth_price_usd = tokens_price["ETH"]

    raw_txs = block["transactions"]
    txs = [
        TransactionSwapSchema.model_validate(s).model_dump(by_alias=True)
        for s in raw_txs
    ]
    detected = []
    swap_single_sandwiches = []
    n = len(txs)

    for i, tf in enumerate(txs):
        searcher_addr = tf["from"]
        pool = tf["to"]
        token_in = tf["tokenIn"]
        token_out = tf["tokenOut"]

        # Skip swaps sem info
        if not (token_in and token_out):
            continue

        # Busca do back-run após o front-run
        for k in range(i + 1, n):
            tb = txs[k]
            # Critério de back-run: mesmo searcher, mesmo pool, swap invertido
            if (
                tb["from"] == searcher_addr
                and tb["to"] == pool
                and tb["tokenIn"] == token_out
                and tb["tokenOut"] == token_in
            ):
                # Coleta vítimas ENTRE tf e tb (não precisam ser consecutivas)
                victims = []
                victim_senders = set()
                for j in range(i + 1, k):
                    tv = txs[j]
                    if (
                        tv["to"] == pool
                        and tv["tokenIn"] == token_in
                        and tv["tokenOut"] == token_out
                        and tv["from"] != searcher_addr
                    ):
                        victims.append(tv)
                        victim_senders.add(tv["from"])
                if len(victims) >= 1:

                    def _get_amount(val, token_decimals):
                        try:
                            # if not token_decimals:
                            #     token_decimals = 18
                            return float(val) / (10**token_decimals)
                        except Exception:
                            return 0.0

                    if token_in not in tokens_decimals:
                        tokens_decimals[token_in] = await get_token_decimals(
                            tf["tokenInAddress"]
                        )
                    token_in_decimals = tokens_decimals[token_in]

                    if token_in not in tokens_price:
                        tokens_price[token_in] = await get_binance_price(token_in)
                    token_in_price_usd = tokens_price[token_in]

                    tb_token_out = tb["tokenOut"]
                    tb_token_out_addr = tb.get("tokenOutAddress")
                    if tb_token_out not in tokens_decimals:
                        tokens_decimals[tb_token_out] = await get_token_decimals(
                            tb_token_out_addr
                        )
                    tb_token_out_decimals = tokens_decimals[tb_token_out]

                    if tb_token_out not in tokens_price:
                        tokens_price[tb_token_out] = await get_binance_price(
                            tb_token_out
                        )
                    tb_token_out_price_usd = tokens_price[tb_token_out]

                    # ---------- GÁS (front) ----------
                    front_gas_used = float(tf.get("gasUsed", 0))
                    front_gas_price = float(tf.get("gasPrice", 0))
                    # EIP-1559
                    front_burned_eth = front_gas_used * base_fee_per_gas / 1e18
                    front_tipped_eth = (
                        front_gas_used * max(front_gas_price - base_fee_per_gas, 0)
                    ) / 1e18
                    front_burned_usd = front_burned_eth * eth_price_usd
                    front_tipped_usd = front_tipped_eth * eth_price_usd

                    # ---------- GÁS (back) ----------
                    back_gas_used = float(tb.get("gasUsed", 0))
                    back_gas_price = float(tb.get("gasPrice", 0))
                    back_burned_eth = (back_gas_used * base_fee_per_gas) / 1e18
                    back_tipped_eth = (
                        back_gas_used * max(back_gas_price - base_fee_per_gas, 0)
                    ) / 1e18
                    back_burned_usd = back_burned_eth * eth_price_usd
                    back_tipped_usd = back_tipped_eth * eth_price_usd

                    cost_amount = 0
                    gain_amount = 0
                    cost_usd = 0
                    gain_usd = 0

                    if token_in_price_usd and token_in_decimals:
                        cost_amount = _get_amount(
                            tf.get("amountIn", 0), token_in_decimals
                        )
                        gain_amount = _get_amount(
                            tb.get("amountOut", 0), tb_token_out_decimals
                        )
                        cost_usd = cost_amount * token_in_price_usd
                        gain_usd = gain_amount * tb_token_out_price_usd

                    total_cost_usd = cost_usd + front_burned_usd + front_tipped_usd
                    total_gain_usd = gain_usd - (back_burned_usd + back_tipped_usd)

                    victims_txs = [f'{v["hash"]}_{v["log_index"]}' for v in victims]
                    swap_single_sandwiches.append(
                        {
                            "block": block["number"],
                            "attacker_addr": searcher_addr,
                            "victims_addr": list(victim_senders),
                            "front_run": tf["hash"],
                            "front_run_log_index": tf["log_index"],
                            "victims_txs": victims_txs,
                            "back_run": tb["hash"],
                            "back_run_log_index": tb["log_index"],
                            "cost_amount": cost_amount,
                            "gain_amount": gain_amount,
                            "cost_usd": total_cost_usd,
                            "gain_usd": total_gain_usd,
                            "front_burned_eth": front_burned_eth,
                            "front_tipped_eth": front_tipped_eth,
                            "back_burned_eth": back_burned_eth,
                            "back_tipped_eth": back_tipped_eth,
                            "front_burned_usd": front_burned_usd,
                            "front_tipped_usd": front_tipped_usd,
                            "back_burned_usd": back_burned_usd,
                            "back_tipped_usd": back_tipped_usd,
                        }
                    )
                    print(
                        "Sandwich detected:",
                        {
                            "block": block["number"],
                            "attacker_addr": searcher_addr,
                            "victims_addr": list(victim_senders),
                            "front_run": tf["hash"],
                            "back_run": tb["hash"],
                            "victims_txs": victims_txs,
                            "cost_usd": total_cost_usd,
                            "gain_usd": total_gain_usd,
                        },
                    )

    sandwich_groups = defaultdict(list)
    for s in swap_single_sandwiches:
        key = (s["front_run"], s["back_run"])
        sandwich_groups[key].append(s)

    for (front_run, back_run), group in sandwich_groups.items():
        if len(group) > 1 or len(group[0]["victims_addr"]) > 1:
            # Concatena os campos victims_addr e victims_txs
            victims_addr = []
            victims_txs = []
            for g in group:
                victims_addr.extend(g["victims_addr"])
                victims_txs.extend(g["victims_txs"])

            # Remove duplicatas
            victims_addr = list(set(victims_addr))
            victims_txs = list(set(victims_txs))

            # Usa o primeiro como base e atualiza os campos concatenados
            merged = group[0].copy()
            merged["victims_addr"] = victims_addr
            merged["victims_txs"] = victims_txs

            merged["front_run"] = list(
                set([f'{g["front_run"]}_{g["front_run_log_index"]}' for g in group])
            )
            merged["back_run"] = list(
                set([f'{g["back_run"]}_{g["back_run_log_index"]}' for g in group])
            )

            merged["cost_usd"] = sum(
                g["cost_usd"]
                for idx, g in enumerate(group)
                if g["front_run"] not in [group[j]["front_run"] for j in range(idx)]
            )
            merged["gain_usd"] = sum(
                g["gain_usd"]
                for idx, g in enumerate(group)
                if g["back_run"] not in [group[j]["back_run"] for j in range(idx)]
            )

            detected.append(merged)

    return detected


async def detect_cross_dex_sandwiches(block):
    """
    Detecta ataques sanduíche entre múltiplas DEXes (Cross-DEX Sandwich).

    :param block: bloco contendo lista de transações (cada tx com: from, to, token_in, token_out, hash, dex_label, amount_in, amount_out)
    :param dex_labels: dicionário mapeando endereço do pool para nome da DEX (ex: {address1: "Uniswap V2", address2: "Uniswap V3"})
    :return: lista de ataques detectados
    """
    dex_labels = {}

    for tx in block["transactions"]:
        pool = tx["to"]
        if pool not in dex_labels:
            dex_name = tx.get("dex_label", "UNKNOWN")
            dex_labels[pool] = dex_name

    txs = block["transactions"]
    n = len(txs)
    detected = []

    # Indexa transações por endereço, dex e token
    dex_pools = {}
    for addr, label in dex_labels.items():
        dex_pools.setdefault(label, set()).add(addr)

    for i, tf1 in enumerate(txs):
        attacker = tf1["from"]
        pool1 = tf1["to"]
        dex1 = dex_labels.get(pool1, "UNKNOWN")
        token_in1 = tf1["tokenIn"]
        token_out1 = tf1["tokenOut"]

        # Ignora swaps incompletos ou pools desconhecidos
        if not (token_in1 and token_out1) or dex1 == "UNKNOWN":
            continue

        # Procura próximo swap do atacante em outra DEX como parte do front-run
        for j in range(i + 1, n):
            tf2 = txs[j]
            if (
                tf2["from"] == attacker
                and tf2["to"] != pool1
                and dex_labels.get(tf2["to"], "UNKNOWN") != "UNKNOWN"
                and dex_labels[tf2["to"]] != dex1
            ):
                pool2 = tf2["to"]
                dex2 = dex_labels[pool2]
                token_in2 = tf2["tokenIn"]
                token_out2 = tf2["tokenOut"]

                # Agora procura por swap da vítima na DEX B
                for k in range(j + 1, n):
                    tv = txs[k]
                    if (
                        tv["to"] == pool2
                        and tv["from"] != attacker
                        and tv["tokenIn"] == token_in2
                        and tv["tokenOut"] == token_out2
                    ):
                        victim = tv["from"]

                        # Procura back-run do atacante na mesma DEX/pool logo após a vítima
                        for m in range(k + 1, n):
                            tb = txs[m]
                            if (
                                tb["from"] == attacker
                                and tb["to"] == pool2
                                and tb["tokenIn"] == token_out2
                                and tb["tokenOut"] == token_in2
                            ):
                                # (Opcional) Checa se há ciclo de arbitragem — atacante voltando à DEX inicial
                                post_sandwich = []
                                for nidx in range(m + 1, n):
                                    ta = txs[nidx]
                                    if (
                                        ta["from"] == attacker
                                        and ta["to"] == pool1
                                        and ta["tokenIn"] == token_out1
                                        and ta["tokenOut"] == token_in1
                                    ):
                                        post_sandwich.append(ta["hash"])
                                detected.append(
                                    {
                                        "block": block["number"],
                                        "front_run_dex_a": tf1["hash"],
                                        "front_run_dex_b": tf2["hash"],
                                        "victim": tv["hash"],
                                        "back_run": tb["hash"],
                                        "attacker": attacker,
                                        "pool_a": pool1,
                                        "pool_b": pool2,
                                        "dex_a": dex1,
                                        "dex_b": dex2,
                                        "arbitrage_cycle": post_sandwich,
                                    }
                                )
                                break
                        break  # vítima encontrada, não precisa olhar mais swaps
                break  # front-run em outra DEX já encontrado
    return detected
