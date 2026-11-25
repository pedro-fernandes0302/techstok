from app import app


def test_sem_login_e_sem_permissao_nao_alteram_dados(
    database, operador, snapshot,
):
    antes = snapshot()
    conn = database.get_db()
    try:
        contagens = {
            tabela: conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
            for tabela in ("categoria", "fornecedor", "produtos")
        }
    finally:
        conn.close()

    anonimo = app.test_client()
    assert anonimo.post("/api/vendas", json={
        "id_cliente": 1, "itens": [{"id_produto": 1, "quantidade": 1}],
    }).status_code == 401
    assert anonimo.post("/api/movimentacoes", json={
        "produto_id": 1, "tipo": "SAIDA", "quantidade": 1,
    }).status_code == 401

    assert operador.post("/api/categorias", json={"nome": "Sem acesso"}).status_code == 403
    assert operador.post("/api/fornecedores", json={
        "razao_social": "Sem acesso", "cnpj": "98765432000199",
        "telefone": "62999990000", "email": "sem-acesso@test.test",
    }).status_code == 403
    assert operador.post("/api/produtos", json={
        "sku": "SEM-ACESSO", "nome": "Sem acesso", "fabricante": "Teste",
        "tipo": "Hardware", "preco": 10, "localizacao": "A1",
        "categoria_id": 1, "fornecedor_id": 1,
    }).status_code == 403
    assert operador.delete("/api/produtos/1").status_code == 403

    assert snapshot() == antes
    conn = database.get_db()
    try:
        for tabela, quantidade in contagens.items():
            assert conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0] == quantidade
    finally:
        conn.close()
