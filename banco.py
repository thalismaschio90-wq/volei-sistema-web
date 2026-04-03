import psycopg2
import os
from psycopg2.extras import RealDictCursor


# =========================================================
# CONEXÃO COM BANCO (SUPABASE)
# =========================================================
def conectar():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise Exception("DATABASE_URL não configurada no Render.")

    return psycopg2.connect(
        database_url,
        cursor_factory=RealDictCursor
    )


# =========================================================
# CRIAR TABELAS
# =========================================================
def criar_tabelas():
    conn = conectar()
    cur = conn.cursor()

    # 🔥 TABELA PRINCIPAL (onde vai todo teu sistema em JSON)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS configuracoes (
        chave TEXT PRIMARY KEY,
        valor TEXT NOT NULL
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


# =========================================================
# GARANTIR ADMIN PADRÃO
# =========================================================
def criar_admin_padrao():
    import json

    conn = conectar()
    cur = conn.cursor()

    # verifica se já existe dados salvos
    cur.execute("SELECT valor FROM configuracoes WHERE chave = 'dados_json'")
    resultado = cur.fetchone()

    if not resultado:
        # cria estrutura inicial
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
            VALUES ('dados_json', %s)
        """, (json.dumps(dados_iniciais, ensure_ascii=False),))

    conn.commit()
    cur.close()
    conn.close()