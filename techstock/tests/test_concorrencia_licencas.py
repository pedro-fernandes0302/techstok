import threading

from app import app


def _client():
    client = app.test_client()
    with client.session_transaction() as session:
        session.update({
            "id_usuario": 2, "nome": "Operador",
            "email": "operador@techstore.com", "perfil": "OPERADOR",
        })
    return client


def test_licencas_digitais_sao_entregues_uma_unica_vez(database, produtos):
    produto_id = produtos["SOFT001"]
    quantidade_tentativas = 8
    barreira = threading.Barrier(quantidade_tentativas)
    resultados = []
    lock = threading.Lock()

    def vender():
        client = _client()
        barreira.wait(timeout=10)
        response = client.post("/api/vendas", json={
            "id_cliente": 1,
            "itens": [{"id_produto": produto_id, "quantidade": 1}],
        })
        with lock:
            resultados.append(response.status_code)

    threads = [
        threading.Thread(target=vender) for _ in range(quantidade_tentativas)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=40)

    assert all(not thread.is_alive() for thread in threads)
    assert resultados.count(201) == 2
    assert resultados.count(409) == quantidade_tentativas - 2

    conn = database.get_db()
    try:
        chaves_entregues = conn.execute(
            """SELECT id_licenca, id_venda FROM ativos_digitais
               WHERE id_produto=? AND id_venda IS NOT NULL""",
            (produto_id,),
        ).fetchall()
        assert len(chaves_entregues) == 2
        assert len({row["id_licenca"] for row in chaves_entregues}) == 2
        for row in conn.execute(
            "SELECT id_venda, quantidade FROM itens_venda WHERE id_produto=?",
            (produto_id,),
        ):
            assert conn.execute(
                "SELECT COUNT(*) FROM ativos_digitais WHERE id_venda=? AND id_produto=?",
                (row["id_venda"], produto_id),
            ).fetchone()[0] == row["quantidade"]
    finally:
        conn.close()
