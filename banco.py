import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()


# =========================================================
# CONEXÃO
# =========================================================
def conectar():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise Exception("DATABASE_URL não configurada.")

    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


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
# OBTER DADOS
# =========================================================
def obter_dados():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        "SELECT valor FROM configuracoes WHERE chave = %s",
        ("dados_json",)
    )
    resultado = cur.fetchone()

    cur.close()
    conn.close()

    if resultado:
        return json.loads(resultado["valor"])
    else:
        return None


# =========================================================
# SALVAR DADOS
# =========================================================
def salvar_dados(dados):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO configuracoes (chave, valor)
        VALUES (%s, %s)
        ON CONFLICT (chave)
        DO UPDATE SET valor = EXCLUDED.valor
    """, (
        "dados_json",
        json.dumps(dados, ensure_ascii=False)
    ))

    conn.commit()
    cur.close()
    conn.close()


# =========================================================
# INICIALIZAÇÃO
# =========================================================
def inicializar_banco():
    criar_tabelas()

    dados = obter_dados()

    if not dados:
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
            "equipes": {}
        }

        salvar_dados(dados_iniciais)