import psycopg2
import os
from psycopg2.extras import RealDictCursor
import json


# =========================================================
# CONEXÃO
# =========================================================
def conectar():
    url = os.environ.get("DATABASE_URL")

    if not url:
        raise Exception("DATABASE_URL não configurada")

    return psycopg2.connect(url, cursor_factory=RealDictCursor)


# =========================================================
# CRIAR TABELAS
# =========================================================
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


# =========================================================
# CARREGAR DADOS
# =========================================================
def carregar_dados():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT valor FROM configuracoes WHERE chave = 'dados_json'")
    resultado = cur.fetchone()

    if resultado:
        dados = json.loads(resultado["valor"])
    else:
        dados = dados_padrao()
        salvar_dados(dados)

    cur.close()
    conn.close()

    return dados


# =========================================================
# SALVAR DADOS
# =========================================================
def salvar_dados(dados):
    conn = conectar()
    cur = conn.cursor()

    dados_json = json.dumps(dados, ensure_ascii=False)

    cur.execute("""
        INSERT INTO configuracoes (chave, valor)
        VALUES ('dados_json', %s)
        ON CONFLICT (chave)
        DO UPDATE SET valor = EXCLUDED.valor
    """, (dados_json,))

    conn.commit()
    cur.close()
    conn.close()


# =========================================================
# DADOS PADRÃO
# =========================================================
def dados_padrao():
    return {
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
        "configuracoes": {}
    }