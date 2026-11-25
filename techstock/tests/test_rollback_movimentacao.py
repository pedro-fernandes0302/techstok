import sqlite3

import routers.api as api


def test_movimentacoes_invalidas_nao_alteram_dados(database, operador, produtos, snapshot):
    antes = snapshot()
    requests = (
        ({"produto_id": 9999, "tipo": "ENTRADA", "quantidade": 1}, 404),
        ({"produto_id": produtos["PROC001"], "tipo": "ENTRADA", "quantidade": 0}, 400),
        ({"produto_id": produtos["PROC001"], "tipo": "SAIDA", "quantidade": -1}, 400),
        ({"produto_id": produtos["PER001"], "tipo": "SAIDA", "quantidade": 2}, 409),
    )
    for payload, expected_status in requests:
        response = operador.post("/api/movimentacoes", json=payload)
        assert response.status_code == expected_status
        assert snapshot() == antes


def test_falha_apos_alterar_saldo_reverte_movimentacao(
    database, operador, produtos, snapshot, monkeypatch,
):
    antes = snapshot()

    def falhar_ao_registrar(*_args, **_kwargs):
        raise sqlite3.IntegrityError("falha injetada após atualização do saldo")

    monkeypatch.setattr(api, "gravar_movimentacao", falhar_ao_registrar)
    response = operador.post("/api/movimentacoes", json={
        "produto_id": produtos["PROC001"],
        "tipo": "SAIDA",
        "quantidade": 1,
    })
    assert response.status_code == 500
    assert snapshot() == antes
