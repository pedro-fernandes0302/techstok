import random
import sqlite3
import threading

from app import app
import pytest


def _client():
    client = app.test_client()
    with client.session_transaction() as session:
        session.update({
            "id_usuario": 2, "nome": "Operador",
            "email": "operador@techstore.com", "perfil": "OPERADOR",
        })
    return client


def test_saldos_e_vendas_sempre_batem_com_livro_razao(database, operador, produtos):
    aleatorio = random.Random(731)
    for _ in range(24):
        produto_id = produtos[aleatorio.choice(("PROC001", "RAM001", "SSD001"))]
        acao = aleatorio.choice(("ENTRADA", "SAIDA", "VENDA"))
        client = _client()
        if acao == "VENDA":
            client.post("/api/vendas", json={
                "id_cliente": 1,
                "itens": [{"id_produto": produto_id, "quantidade": 1}],
            })
        else:
            client.post("/api/movimentacoes", json={
                "produto_id": produto_id, "tipo": acao, "quantidade": 1,
            })

    produto_id = produtos["PER001"]
    barreira = threading.Barrier(2)
    status = []
    lock = threading.Lock()

    def requisitar(tipo):
        client = _client()
        barreira.wait(timeout=10)
        if tipo == "VENDA":
            response = client.post("/api/vendas", json={
                "id_cliente": 1,
                "itens": [{"id_produto": produto_id, "quantidade": 1}],
            })
        else:
            response = client.post("/api/movimentacoes", json={
                "produto_id": produto_id, "tipo": "SAIDA", "quantidade": 1,
            })
        with lock:
            status.append(response.status_code)

    threads = [
        threading.Thread(target=requisitar, args=("VENDA",)),
        threading.Thread(target=requisitar, args=("SAIDA",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=40)
    assert all(not thread.is_alive() for thread in threads)
    assert sorted(status) == [201, 409]

    conn = database.get_db()
    try:
        saldos = conn.execute(
            "SELECT id_produto, estoque_atual FROM produtos ORDER BY id_produto"
        ).fetchall()
        for row in saldos:
            entradas = conn.execute(
                """SELECT COALESCE(SUM(quantidade), 0) FROM movimentacoes
                   WHERE id_produto=? AND tipo='ENTRADA'""",
                (row["id_produto"],),
            ).fetchone()[0]
            saidas = conn.execute(
                """SELECT COALESCE(SUM(quantidade), 0) FROM movimentacoes
                   WHERE id_produto=? AND tipo='SAIDA'""",
                (row["id_produto"],),
            ).fetchone()[0]
            assert row["estoque_atual"] == entradas - saidas
            assert row["estoque_atual"] >= 0

        vendas = conn.execute("SELECT id_venda FROM vendas").fetchall()
        for venda in vendas:
            itens = conn.execute(
                """SELECT id_produto, quantidade FROM itens_venda
                   WHERE id_venda=? ORDER BY id_produto""",
                (venda["id_venda"],),
            ).fetchall()
            movimentos = conn.execute(
                """SELECT id_produto, quantidade, tipo FROM movimentacoes
                   WHERE id_venda=? ORDER BY id_produto""",
                (venda["id_venda"],),
            ).fetchall()
            assert itens
            assert len(itens) == len(movimentos)
            assert [
                (item["id_produto"], item["quantidade"]) for item in itens
            ] == [
                (mov["id_produto"], mov["quantidade"])
                for mov in movimentos if mov["tipo"] == "SAIDA"
            ]
    finally:
        conn.close()


def test_migracao_instala_travas_de_saldo_sem_perder_dados(database, produtos):
    conn = database.get_db()
    try:
        conn.execute("DROP TRIGGER produtos_estoque_nao_negativo_insert")
        conn.execute("DROP TRIGGER produtos_estoque_nao_negativo_update")
        conn.commit()
    finally:
        conn.close()

    database.ensure_database()
    conn = database.get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="estoque_atual"):
            conn.execute(
                "UPDATE produtos SET estoque_atual=-1 WHERE id_produto=?",
                (produtos["PROC001"],),
            )
        conn.rollback()
        assert conn.execute(
            "SELECT estoque_atual FROM produtos WHERE id_produto=?",
            (produtos["PROC001"],),
        ).fetchone()[0] == 10
    finally:
        conn.close()


def test_migracao_preserva_banco_se_houver_saldo_negativo_legado(database, produtos):
    conn = database.get_db()
    try:
        conn.execute("DROP TRIGGER produtos_estoque_nao_negativo_insert")
        conn.execute("DROP TRIGGER produtos_estoque_nao_negativo_update")
        conn.execute("PRAGMA ignore_check_constraints=ON")
        conn.execute(
            "UPDATE produtos SET estoque_atual=-1 WHERE id_produto=?",
            (produtos["PROC001"],),
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RuntimeError, match="Reconcilie o Livro-Razão"):
        database.ensure_database()
    conn = database.get_db()
    try:
        assert conn.execute(
            "SELECT estoque_atual FROM produtos WHERE id_produto=?",
            (produtos["PROC001"],),
        ).fetchone()[0] == -1
    finally:
        conn.close()


def test_cadastro_de_produto_registra_estoque_inicial_no_livro(
    database, gerente,
):
    response = gerente.post("/api/produtos", json={
        "sku": "NOVO-API-ESTOQUE", "nome": "Produto inicial API",
        "fabricante": "Teste", "tipo": "Hardware", "preco": "12.50",
        "estoque_atual": 4, "estoque_minimo": 1, "localizacao": "A1",
        "categoria_id": 1, "fornecedor_id": 1,
    })
    assert response.status_code == 201

    html = gerente.post("/produtos/novo", data={
        "sku": "NOVO-HTML-ESTOQUE", "nome": "Produto inicial HTML",
        "fabricante": "Teste", "tipo": "Hardware", "preco": "12.50",
        "estoque_atual": "3", "estoque_minimo": "1", "localizacao": "A2",
        "categoria_id": "1", "fornecedor_id": "1",
    })
    assert html.status_code == 302, html.data.decode("utf-8")

    conn = database.get_db()
    try:
        rows = conn.execute("""
            SELECT p.estoque_atual, m.tipo, m.quantidade
            FROM produtos p JOIN movimentacoes m ON m.id_produto=p.id_produto
            WHERE p.sku IN ('NOVO-API-ESTOQUE', 'NOVO-HTML-ESTOQUE')
            ORDER BY p.sku
        """).fetchall()
        assert [(row["estoque_atual"], row["tipo"], row["quantidade"]) for row in rows] == [
            (4, "ENTRADA", 4), (3, "ENTRADA", 3),
        ]
    finally:
        conn.close()
