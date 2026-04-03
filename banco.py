import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor


def conectar():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise Exception("DATABASE_URL não configurada no Render.")

    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def criar_tabelas():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def criar_admin_padrao():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT valor FROM configuracoes WHERE chave = %s", ("dados_json",))
    resultado = cur.fetchone()

    if not resultado:
        dados_iniciais = {
            "usuarios": {
                "admin": {
                    "nome": "Administrador",
                    "senha": "123",
                    "perfil": "superadmin",
                    "ativo": True,
                    "equipe": None
                }
            },
            "equipes": {},
            "competicoes": {},
            "configuracoes": {
                "prazo_cadastro_atletas": "",
                "prazo_edicao_atletas": ""
            }
        }

        cur.execute("""
            INSERT INTO configuracoes (chave, valor)
            VALUES (%s, %s)
            ON CONFLICT (chave)
            DO NOTHING
        """, ("dados_json", json.dumps(dados_iniciais, ensure_ascii=False)))

    conn.commit()
    cur.close()
    conn.close()
