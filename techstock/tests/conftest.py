import os
import tempfile

import pytest

_bootstrap = tempfile.TemporaryDirectory()
os.environ["TECHSTOCK_DATABASE"] = os.path.join(_bootstrap.name, "import.db")

import db
from app import app


@pytest.fixture
def database(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DATABASE", str(tmp_path / "test-techstock.db"))
    app.config.update(TESTING=True)
    db.init_db()
    yield db


def _client(profile):
    client = app.test_client()
    user_id = 1 if profile == "GERENTE" else 2
    with client.session_transaction() as session:
        session.update({
            "id_usuario": user_id,
            "nome": "Gerente de teste" if user_id == 1 else "Operador de teste",
            "email": "gerente@techstore.com" if user_id == 1 else "operador@techstore.com",
            "perfil": profile,
        })
    return client


@pytest.fixture
def gerente(database):
    return _client("GERENTE")


@pytest.fixture
def operador(database):
    return _client("OPERADOR")


@pytest.fixture
def produtos(database):
    conn = database.get_db()
    try:
        return {
            row["sku"]: row["id_produto"]
            for row in conn.execute("SELECT id_produto, sku FROM produtos")
        }
    finally:
        conn.close()


@pytest.fixture
def produtos_exemplo(database, produtos):
    conn = database.get_db()
    try:
        digital = conn.execute(
            """SELECT p.id_produto, p.estoque_atual,
                      COUNT(a.id_licenca) AS chaves_disponiveis
               FROM produtos p LEFT JOIN ativos_digitais a
                 ON a.id_produto=p.id_produto AND a.id_venda IS NULL
               WHERE p.sku='SOFT001' GROUP BY p.id_produto"""
        ).fetchone()
        return {
            "fisico": {
                "id_produto": produtos["PROC001"],
                "estoque": conn.execute(
                    "SELECT estoque_atual FROM produtos WHERE sku='PROC001'"
                ).fetchone()[0],
            },
            "digital": dict(digital),
        }
    finally:
        conn.close()


@pytest.fixture
def snapshot(database):
    def capturar():
        conn = database.get_db()
        try:
            return {
                tabela: [
                    tuple(row) for row in conn.execute(
                        f"SELECT * FROM {tabela} ORDER BY 1"
                    )
                ]
                for tabela in (
                    "produtos", "vendas", "itens_venda", "movimentacoes",
                    "ativos_digitais",
                )
            }
        finally:
            conn.close()
    return capturar
