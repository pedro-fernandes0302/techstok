import sqlite3
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from db import get_db, run_write_transaction

bp = Blueprint("nova_movimentacao", __name__)


class EstoqueInsuficiente(Exception):
    pass


class ProdutoNaoEncontrado(Exception):
    pass


class ProdutoDigital(Exception):
    pass


@bp.route("/movimentacoes/nova", methods=["GET", "POST"])
def nova_movimentacao():
    conn = get_db()
    try:
        produtos = conn.execute(
            "SELECT id_produto AS id, sku, nome_produto AS nome, estoque_atual "
            "FROM produtos WHERE tipo != 'Software' ORDER BY nome"
        ).fetchall()
        if request.method == "GET":
            return render_template("movimentacao_form.html", produtos=produtos, dados={})
        dados = {
            campo: request.form.get(campo, "")
            for campo in ("produto_id", "tipo", "quantidade", "observacao")
        }
        try:
            produto_id = int(dados["produto_id"])
            quantidade = int(dados["quantidade"])
        except (TypeError, ValueError):
            flash("Produto e quantidade devem ser válidos.", "danger")
            return render_template("movimentacao_form.html", produtos=produtos, dados=dados), 400
        if quantidade <= 0:
            flash("A quantidade deve ser um número inteiro maior que zero.", "danger")
            return render_template("movimentacao_form.html", produtos=produtos, dados=dados), 400
        if dados["tipo"] not in ("ENTRADA", "SAIDA"):
            flash("Tipo de movimentação inválido.", "danger")
            return render_template("movimentacao_form.html", produtos=produtos, dados=dados), 400

        try:
            def registrar():
                produto = conn.execute(
                    """SELECT estoque_atual, estoque_minimo, tipo
                       FROM produtos WHERE id_produto = ?""",
                    (produto_id,),
                ).fetchone()
                if not produto:
                    raise ProdutoNaoEncontrado
                if produto["tipo"] == "Software":
                    raise ProdutoDigital
                incremento = quantidade if dados["tipo"] == "ENTRADA" else -quantidade
                cursor = conn.execute(
                    """UPDATE produtos SET estoque_atual = estoque_atual + ?
                       WHERE id_produto = ? AND estoque_atual + ? >= 0""",
                    (incremento, produto_id, incremento),
                )
                if cursor.rowcount != 1:
                    saldo = conn.execute(
                        "SELECT estoque_atual FROM produtos WHERE id_produto = ?",
                        (produto_id,),
                    ).fetchone()[0]
                    raise EstoqueInsuficiente(saldo)
                conn.execute(
                    """INSERT INTO movimentacoes
                       (id_produto, id_usuario, tipo, quantidade, observacao)
                       VALUES (?, ?, ?, ?, ?)""",
                    (produto_id, session["id_usuario"],
                     "ENTRADA" if incremento > 0 else "SAIDA",
                     quantidade, dados["observacao"].strip() or None),
                )
                saldo = conn.execute(
                    """SELECT estoque_atual, estoque_minimo FROM produtos
                       WHERE id_produto = ?""",
                    (produto_id,),
                ).fetchone()
                return saldo["estoque_atual"] <= saldo["estoque_minimo"]

            aviso_reposicao = run_write_transaction(conn, registrar)
            if aviso_reposicao:
                flash(
                    "Movimentação registrada. Atenção: o novo saldo atingiu o nível mínimo e precisa ser reposto.",
                    "warning",
                )
            else:
                flash("Movimentação registrada com sucesso.", "success")
            return redirect(url_for("historico_movimentacoes.historico_movimentacoes"))
        except ProdutoNaoEncontrado:
            conn.rollback()
            flash("Produto não encontrado.", "danger")
            return render_template("movimentacao_form.html", produtos=produtos, dados=dados), 404
        except ProdutoDigital:
            conn.rollback()
            flash("Licenças digitais só movimentam por venda ou cadastro de chaves.", "danger")
            return render_template("movimentacao_form.html", produtos=produtos, dados=dados), 409
        except EstoqueInsuficiente as exc:
            conn.rollback()
            flash(
                f"Estoque insuficiente: saldo atual {exc}, solicitado {quantidade}",
                "danger",
            )
            return render_template("movimentacao_form.html", produtos=produtos, dados=dados), 400
        except (sqlite3.Error, ValueError):
            conn.rollback()
            flash("Não foi possível registrar a movimentação. Verifique os dados e tente novamente.", "danger")
            return render_template("movimentacao_form.html", produtos=produtos, dados=dados), 400
    finally:
        conn.close()
