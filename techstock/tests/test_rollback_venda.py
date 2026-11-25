import sqlite3

import routers.api as api


def test_venda_com_segundo_item_sem_estoque_reverte_tudo(
    database, operador, produtos, snapshot,
):
    antes = snapshot()
    resposta = operador.post("/api/vendas", json={
        "id_cliente": 1,
        "itens": [
            {"id_produto": produtos["PROC001"], "quantidade": 1},
            {"id_produto": produtos["PER001"], "quantidade": 2},
            {"id_produto": produtos["RAM001"], "quantidade": 1},
        ],
    })
    assert resposta.status_code == 409
    assert "Estoque insuficiente" in resposta.json["erro"]
    assert snapshot() == antes


def test_falha_apos_baixa_e_reserva_de_chave_reverte_venda(
    database, operador, produtos, snapshot, monkeypatch,
):
    antes = snapshot()
    gravacao_original = api.gravar_movimentacao_venda
    produto_digital = produtos["SOFT001"]

    def falhar_depois_da_reserva(
        conn, produto_id, venda_id, usuario_id, quantidade, numero_pedido,
    ):
        if produto_id == produto_digital:
            raise sqlite3.IntegrityError("falha injetada após reserva da licença")
        gravacao_original(
            conn, produto_id, venda_id, usuario_id, quantidade, numero_pedido,
        )

    monkeypatch.setattr(api, "gravar_movimentacao_venda", falhar_depois_da_reserva)
    resposta = operador.post("/api/vendas", json={
        "id_cliente": 1,
        "itens": [
            {"id_produto": produtos["PROC001"], "quantidade": 1},
            {"id_produto": produto_digital, "quantidade": 1},
        ],
    })
    assert resposta.status_code == 500
    assert snapshot() == antes


def test_reenvio_com_idempotency_key_nao_cria_venda_duplicada(
    database, operador, produtos,
):
    headers = {"Idempotency-Key": "demo-retry-001"}
    payload = {
        "id_cliente": 1,
        "itens": [{"id_produto": produtos["PROC001"], "quantidade": 1}],
    }
    primeira = operador.post("/api/vendas", json=payload, headers=headers)
    repetida = operador.post("/api/vendas", json=payload, headers=headers)
    assert primeira.status_code == 201
    assert repetida.status_code == 201
    assert repetida.json == primeira.json
    conn = database.get_db()
    try:
        assert conn.execute("SELECT COUNT(*) FROM vendas").fetchone()[0] == 1
        assert conn.execute(
            "SELECT estoque_atual FROM produtos WHERE id_produto=?",
            (produtos["PROC001"],),
        ).fetchone()[0] == 9
    finally:
        conn.close()

    diferente = operador.post("/api/vendas", json={
        "id_cliente": 1,
        "itens": [{"id_produto": produtos["RAM001"], "quantidade": 1}],
    }, headers=headers)
    assert diferente.status_code == 409
