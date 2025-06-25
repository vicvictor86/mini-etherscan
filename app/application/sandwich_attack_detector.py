from fastapi import Request


async def detect_single_dex_sandwiches(request: Request, block, amount_tol=0.01):
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
                #     abs(float(ta1["amountOut"]) - float(ta2["amountIn"]))
                #     / float(ta1["amountOut"])
                #     > amount_tol
                # ):
                #     continue

                # await save_detected_sandwich(request, block, ta1, tv, ta2)
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
    request: Request, block, amount_tol=0.01
):
    txs = block["transactions"]
    detected = []
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

                if len(victims) > 1:
                    # await save_detected_sandwich(
                    #     request,
                    #     block,
                    #     tf,
                    #     victims,
                    #     tb,
                    #     sandwich_type="multi_layered_burger",
                    # )
                    cost = tf.get("amountIn", 0)  # quanto gastou no front-run
                    gain = tb.get("amountOut", 0)  # quanto recuperou no back-run
                    profit = gain - cost

                    detected.append(
                        {
                            "block": block["number"],
                            "attacker_addr": searcher_addr,
                            "victims_addr": list(victim_senders),
                            "front_run": tf["hash"],
                            "victims_txs": [v["hash"] for v in victims],
                            "back_run": tb["hash"],
                            "cost": cost,
                            "gain": gain,
                            "profit": profit,
                        }
                    )
                # Após encontrar um back-run válido, pare a busca para este tf
                break

    return detected


async def detect_cross_dex_sandwiches(block):
    """
    Detecta ataques sanduíche entre múltiplas DEXes (Cross-DEX Sandwich).

    :param block: bloco contendo lista de transações (cada tx com: from, to, tokenIn, tokenOut, hash, dex_label, amountIn, amountOut)
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
