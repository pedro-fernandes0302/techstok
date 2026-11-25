def _criar_produto(client):
    return client.post("/api/produtos", json={
        "sku": "NOVO-TESTE",
        "nome": "Produto de teste",
        "fabricante": "Teste",
        "tipo": "Hardware",
        "preco": "12.50",
        "estoque_atual": 0,
        "estoque_minimo": 0,
        "localizacao": "A-1",
        "categoria_id": 1,
        "fornecedor_id": 1,
    })


def test_falha_apos_insert_reverte_cadastros(database, gerente):
    conn = database.get_db()
    try:
        for tabela, nome in (
            ("categoria", "categoria"),
            ("fornecedor", "fornecedor"),
            ("produtos", "produto"),
        ):
            conn.execute(f"""
                CREATE TRIGGER falha_insert_{nome} AFTER INSERT ON {tabela}
                BEGIN SELECT RAISE(ABORT, 'falha injetada'); END
            """)
        conn.commit()
        totais_antes = {
            tabela: conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
            for tabela in ("categoria", "fornecedor", "produtos")
        }
    finally:
        conn.close()

    assert gerente.post("/api/categorias", json={"nome": "Categoria Falha"}).status_code == 400
    assert gerente.post("/api/fornecedores", json={
        "razao_social": "Fornecedor Falha", "cnpj": "98765432000199",
        "telefone": "62999990000", "email": "falha@fornecedor.test",
    }).status_code == 400
    assert _criar_produto(gerente).status_code == 400

    conn = database.get_db()
    try:
        for tabela, quantidade in totais_antes.items():
            assert conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0] == quantidade
        assert conn.execute(
            "SELECT COUNT(*) FROM categoria WHERE nome_categoria='Categoria Falha'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM fornecedor WHERE email='falha@fornecedor.test'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM produtos WHERE sku='NOVO-TESTE'"
        ).fetchone()[0] == 0
    finally:
        conn.close()


def test_falha_apos_delete_preserva_registros(database, gerente):
    categoria = gerente.post("/api/categorias", json={"nome": "Categoria Temporaria"})
    fornecedor = gerente.post("/api/fornecedores", json={
        "razao_social": "Fornecedor Temporario", "cnpj": "98765432000199",
        "telefone": "62999990000", "email": "temporario@fornecedor.test",
    })
    produto = _criar_produto(gerente)
    assert categoria.status_code == 201
    assert fornecedor.status_code == 201
    assert produto.status_code == 201
    conn = database.get_db()
    try:
        categoria_id = conn.execute(
            "SELECT id_categoria FROM categoria WHERE nome_categoria='Categoria Temporaria'"
        ).fetchone()[0]
        fornecedor_id = conn.execute(
            "SELECT id_fornecedor FROM fornecedor WHERE email='temporario@fornecedor.test'"
        ).fetchone()[0]
        produto_id = conn.execute(
            "SELECT id_produto FROM produtos WHERE sku='NOVO-TESTE'"
        ).fetchone()[0]
        for tabela, nome in (
            ("categoria", "categoria"),
            ("fornecedor", "fornecedor"),
            ("produtos", "produto"),
        ):
            conn.execute(f"""
                CREATE TRIGGER falha_delete_{nome} AFTER DELETE ON {tabela}
                BEGIN SELECT RAISE(ABORT, 'falha injetada'); END
            """)
        conn.commit()
    finally:
        conn.close()

    assert gerente.delete(f"/api/categorias/{categoria_id}").status_code == 409
    assert gerente.delete(f"/api/fornecedores/{fornecedor_id}").status_code == 409
    assert gerente.delete(f"/api/produtos/{produto_id}").status_code == 409
    conn = database.get_db()
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM categoria WHERE id_categoria=?", (categoria_id,),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM fornecedor WHERE id_fornecedor=?", (fornecedor_id,),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM produtos WHERE id_produto=?", (produto_id,),
        ).fetchone()[0] == 1
    finally:
        conn.close()


def test_nao_exclui_categoria_ou_fornecedor_com_produtos_vinculados(database, gerente):
    categoria = gerente.delete("/api/categorias/1")
    fornecedor = gerente.delete("/api/fornecedores/1")
    assert categoria.status_code == 409
    assert "produtos vinculados" in categoria.json["erro"].lower()
    assert fornecedor.status_code == 409
    assert "produtos vinculados" in fornecedor.json["erro"].lower()
    conn = database.get_db()
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM categoria WHERE id_categoria=1"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM fornecedor WHERE id_fornecedor=1"
        ).fetchone()[0] == 1
    finally:
        conn.close()


def test_nao_exclui_produto_com_historico_vinculado(database, gerente):
    response = gerente.delete("/api/produtos/1")
    assert response.status_code == 409
    assert "histórico" in response.json["erro"].lower()
    conn = database.get_db()
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM produtos WHERE id_produto=1"
        ).fetchone()[0] == 1
    finally:
        conn.close()
