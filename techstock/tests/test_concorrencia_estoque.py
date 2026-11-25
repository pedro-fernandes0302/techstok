import threading

from app import app


def _client_operador():
    client = app.test_client()
    with client.session_transaction() as session:
        session.update({
            "id_usuario": 2, "nome": "Operador", "email": "operador@techstore.com",
            "perfil": "OPERADOR",
        })
    return client


def _largar_juntos(n, acao):
    barreira = threading.Barrier(n)
    resultados = []
    lock = threading.Lock()

    def executar(payload):
        client = _client_operador()
        barreira.wait(timeout=10)
        resposta = acao(client, payload)
        with lock:
            resultados.append((resposta.status_code, resposta.get_json(silent=True)))

    threads = [threading.Thread(target=executar, args=(indice,)) for indice in range(n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=40)
    assert all(not thread.is_alive() for thread in threads), "requisição concorrente travou"
    assert len(resultados) == n
    return resultados


def test_duas_e_dez_vendas_disputam_ultima_unidade_repetidamente(database, produtos):
    produto_id = produtos["PER001"]
    for n in (2, 10):
        for _ in range(3):
            conn = database.get_db()
            try:
                conn.execute(
                    "UPDATE produtos SET estoque_atual=1 WHERE id_produto=?", (produto_id,),
                )
                conn.commit()
            finally:
                conn.close()
            resultados = _largar_juntos(
                n,
                lambda client, _: client.post("/api/vendas", json={
                    "id_cliente": 1,
                    "itens": [{"id_produto": produto_id, "quantidade": 1}],
                }),
            )
            status = [codigo for codigo, _ in resultados]
            assert status.count(201) == 1
            assert status.count(409) == n - 1
            conn = database.get_db()
            try:
                saldo = conn.execute(
                    "SELECT estoque_atual FROM produtos WHERE id_produto=?", (produto_id,),
                ).fetchone()[0]
                assert saldo == 0
                assert saldo >= 0
            finally:
                conn.close()


def test_venda_e_saida_manual_disputam_a_ultima_unidade(database, produtos):
    produto_id = produtos["PER001"]
    barrier = threading.Barrier(2)
    resultados = []
    lock = threading.Lock()

    def vender():
        client = _client_operador()
        barrier.wait(timeout=10)
        response = client.post("/api/vendas", json={
            "id_cliente": 1, "itens": [{"id_produto": produto_id, "quantidade": 1}],
        })
        with lock:
            resultados.append(response.status_code)

    def movimentar():
        client = _client_operador()
        barrier.wait(timeout=10)
        response = client.post("/api/movimentacoes", json={
            "produto_id": produto_id, "tipo": "SAIDA", "quantidade": 1,
        })
        with lock:
            resultados.append(response.status_code)

    threads = [threading.Thread(target=vender), threading.Thread(target=movimentar)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=40)
    assert all(not thread.is_alive() for thread in threads)
    assert sorted(resultados) == [201, 409]
    conn = database.get_db()
    try:
        assert conn.execute(
            "SELECT estoque_atual FROM produtos WHERE id_produto=?", (produto_id,),
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM movimentacoes WHERE id_produto=? AND tipo='SAIDA'",
            (produto_id,),
        ).fetchone()[0] == 1
    finally:
        conn.close()


def test_saida_pela_rota_html_tambem_nao_consume_estoque_concorrente(database, produtos):
    produto_id = produtos["PER001"]
    barreira = threading.Barrier(2)
    resultados = []
    lock = threading.Lock()

    def retirar():
        client = _client_operador()
        barreira.wait(timeout=10)
        response = client.post("/movimentacoes/nova", data={
            "produto_id": str(produto_id), "tipo": "SAIDA",
            "quantidade": "1", "observacao": "teste concorrente",
        })
        with lock:
            resultados.append(response.status_code)

    threads = [threading.Thread(target=retirar) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=40)
    assert all(not thread.is_alive() for thread in threads)
    assert sorted(resultados) == [302, 400]

    conn = database.get_db()
    try:
        assert conn.execute(
            "SELECT estoque_atual FROM produtos WHERE id_produto=?", (produto_id,),
        ).fetchone()[0] == 0
        assert conn.execute(
            """SELECT COUNT(*) FROM movimentacoes
               WHERE id_produto=? AND tipo='SAIDA'""",
            (produto_id,),
        ).fetchone()[0] == 1
    finally:
        conn.close()


def test_vendas_concorrentes_com_itens_em_ordens_diferentes(database, produtos):
    conn = database.get_db()
    try:
        conn.execute("""
            CREATE TABLE ordem_baixas (
                sequencia INTEGER PRIMARY KEY AUTOINCREMENT, id_produto INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TRIGGER rastrear_baixas AFTER UPDATE OF estoque_atual ON produtos
            BEGIN INSERT INTO ordem_baixas (id_produto) VALUES (NEW.id_produto); END
        """)
        conn.commit()
    finally:
        conn.close()

    cargas = (
        [{"id_produto": produtos["PROC001"], "quantidade": 1},
         {"id_produto": produtos["RAM001"], "quantidade": 1}],
        [{"id_produto": produtos["RAM001"], "quantidade": 1},
         {"id_produto": produtos["PROC001"], "quantidade": 1}],
    )
    resultados = _largar_juntos(
        2,
        lambda client, indice: client.post(
            "/api/vendas", json={"id_cliente": 1, "itens": cargas[indice]},
        ),
    )
    assert [codigo for codigo, _ in resultados] == [201, 201]
    conn = database.get_db()
    try:
        baixa = [
            row[0] for row in conn.execute(
                "SELECT id_produto FROM ordem_baixas ORDER BY sequencia"
            )
        ]
        assert baixa == [
            produtos["PROC001"], produtos["RAM001"],
            produtos["PROC001"], produtos["RAM001"],
        ]
        assert conn.execute("SELECT COUNT(*) FROM vendas").fetchone()[0] == 2
    finally:
        conn.close()
