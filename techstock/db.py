import os
import sqlite3
import time
from pathlib import Path

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get("TECHSTOCK_DATABASE", os.path.join(BASE_DIR, "techstock.db"))
EXPECTED_TABLES = {
    "usuarios", "categoria", "fornecedor", "produtos", "movimentacoes",
    "ativos_digitais", "clientes", "vendas", "itens_venda",
}
EXPECTED_TRIGGERS = {
    "movimentacoes_sem_update", "movimentacoes_sem_delete",
    "itens_venda_sem_update", "itens_venda_sem_delete",
    "vendas_sem_delete", "vendas_total_imutavel",
    "produtos_estoque_nao_negativo_insert",
    "produtos_estoque_nao_negativo_update",
}


def get_db():
    """Abre uma conexão SQLite com chaves estrangeiras obrigatórias."""
    conn = sqlite3.connect(DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def run_write_transaction(conn, operation, attempts=3):
    """Repete a transação inteira após contenção SQLite, sem deixar escrita parcial."""
    for tentativa in range(attempts):
        try:
            conn.execute("BEGIN IMMEDIATE")
            resultado = operation()
            conn.commit()
            return resultado
        except sqlite3.OperationalError as exc:
            conn.rollback()
            codigo = getattr(exc, "sqlite_errorcode", None)
            codigo_base = codigo & 0xFF if codigo is not None else None
            bloqueio = codigo_base in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
            bloqueio = bloqueio or "locked" in str(exc).lower() or "busy" in str(exc).lower()
            if not bloqueio or tentativa + 1 == attempts:
                raise
            time.sleep(0.05 * (tentativa + 1))
        except Exception:
            conn.rollback()
            raise
    raise RuntimeError("Transação encerrada sem resultado.")


def seed_usuarios(conn):
    """Mantém as contas de demonstração fora do SQL para armazenar só hashes."""
    usuarios = (
        ("Gerente TechStore", "gerente@techstore.com", "demo-techstore-2026", "GERENTE"),
        ("Operador TechStore", "operador@techstore.com", "operador-techstore-2026", "OPERADOR"),
    )
    for nome, email, senha, perfil in usuarios:
        conn.execute(
            """INSERT OR IGNORE INTO usuarios (nome, email, senha_hash, perfil)
               VALUES (?, ?, ?, ?)""",
            (nome, email, generate_password_hash(senha), perfil),
        )


def init_db():
    """Cria o esquema e os dados de demonstração em banco vazio."""
    conn = get_db()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        # A versão antiga materializava este saldo; removemos só a tabela derivada antes de criar a VIEW.
        tipo_estoque = conn.execute(
            "SELECT type FROM sqlite_master WHERE name = 'estoque_fisico'"
        ).fetchone()
        if tipo_estoque and tipo_estoque["type"] == "table":
            conn.execute("DROP TABLE estoque_fisico")
        script = Path(BASE_DIR, "database.sql").read_text(encoding="utf-8-sig")
        conn.executescript("BEGIN IMMEDIATE;\n" + script)
        seed_usuarios(conn)
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_stock_guards(conn):
    """Completa a trava de saldo em bancos antigos sem alterar o histórico existente."""
    tabelas = {
        row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "produtos" not in tabelas:
        return
    colunas = {
        row["name"] for row in conn.execute("PRAGMA table_info(produtos)")
    }
    if "estoque_atual" not in colunas:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        negativo = conn.execute(
            "SELECT id_produto, estoque_atual FROM produtos WHERE estoque_atual < 0 LIMIT 1"
        ).fetchone()
        if negativo:
            raise RuntimeError(
                "Migração de estoque interrompida: o produto "
                f"{negativo['id_produto']} já possui saldo negativo. "
                "Reconcilie o Livro-Razão antes de aplicar a trava."
            )
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS produtos_estoque_nao_negativo_insert
            BEFORE INSERT ON produtos WHEN NEW.estoque_atual < 0
            BEGIN SELECT RAISE(ABORT, 'estoque_atual não pode ser negativo'); END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS produtos_estoque_nao_negativo_update
            BEFORE UPDATE OF estoque_atual ON produtos WHEN NEW.estoque_atual < 0
            BEGIN SELECT RAISE(ABORT, 'estoque_atual não pode ser negativo'); END
        """)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def ensure_sale_idempotency(conn):
    """Adiciona os metadados opcionais sem reescrever nem descartar vendas antigas."""
    tabelas = {
        row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "vendas" not in tabelas:
        return
    colunas = {
        row["name"] for row in conn.execute("PRAGMA table_info(vendas)")
    }
    if not {"id_usuario", "idempotency_key", "request_hash"}.issubset(colunas):
        conn.execute("BEGIN IMMEDIATE")
        try:
            if "id_usuario" not in colunas:
                conn.rollback()
                return
            if "idempotency_key" not in colunas:
                conn.execute("ALTER TABLE vendas ADD COLUMN idempotency_key TEXT")
            if "request_hash" not in colunas:
                conn.execute("ALTER TABLE vendas ADD COLUMN request_hash TEXT")
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS vendas_idempotency_key_unique
                ON vendas (id_usuario, idempotency_key)
                WHERE idempotency_key IS NOT NULL
            """)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    else:
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS vendas_idempotency_key_unique
            ON vendas (id_usuario, idempotency_key)
            WHERE idempotency_key IS NOT NULL
        """)
        conn.commit()


def ensure_database():
    """Recria o esquema de demonstração quando qualquer objeto obrigatório falta."""
    if not os.path.exists(DATABASE):
        init_db()
        return
    conn = get_db()
    try:
        tabelas = {
            row["name"] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
        triggers = {
            row["name"] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        ensure_sale_idempotency(conn)
        ensure_stock_guards(conn)
        triggers = {
            row["name"] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        precisa_inicializar = (
            not EXPECTED_TABLES.issubset(tabelas)
            or "estoque_fisico" not in tabelas
            or not EXPECTED_TRIGGERS.issubset(triggers)
        )
    finally:
        conn.close()
    if precisa_inicializar:
        if EXPECTED_TABLES & tabelas:
            raise RuntimeError(
                "Banco existente está incompleto. Para evitar perda de dados, nada foi apagado; "
                "faça backup e remova o arquivo do banco para recriá-lo do zero."
            )
        init_db()
    else:
        conn = get_db()
        try:
            seed_usuarios(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
