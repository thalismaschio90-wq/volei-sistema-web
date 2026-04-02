import json
import sqlite3
from pathlib import Path

DB_PATH = "banco.db"


def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def criar_tabelas():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            login TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            equipe TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipes (
            nome TEXT PRIMARY KEY,
            login TEXT NOT NULL,
            senha TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS atletas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipe_nome TEXT NOT NULL,
            nome TEXT NOT NULL,
            numero TEXT,
            cpf TEXT NOT NULL UNIQUE,
            data_nascimento TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente',
            FOREIGN KEY (equipe_nome) REFERENCES equipes(nome)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    conn.commit()
    conn.close()


def banco_vazio():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM usuarios")
    total = cur.fetchone()["total"]
    conn.close()
    return total == 0


def criar_admin_padrao():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT login FROM usuarios WHERE login = ?", ("admin",))
    existe = cur.fetchone()

    if not existe:
        cur.execute("""
            INSERT INTO usuarios (login, nome, senha, perfil, ativo, equipe)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("admin", "Administrador", "123", "superadmin", 1, None))

    conn.commit()
    conn.close()


def importar_json_se_existir(caminho_json="dados.json"):
    arquivo = Path(caminho_json)

    if not arquivo.exists():
        criar_admin_padrao()
        return

    if not banco_vazio():
        return

    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        criar_admin_padrao()
        return

    usuarios = dados.get("usuarios", {})
    equipes = dados.get("equipes", {})

    conn = conectar()
    cur = conn.cursor()

    for login, usuario in usuarios.items():
        cur.execute("""
            INSERT OR IGNORE INTO usuarios (login, nome, senha, perfil, ativo, equipe)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            login,
            usuario.get("nome", login),
            usuario.get("senha", ""),
            usuario.get("perfil", ""),
            1 if usuario.get("ativo", True) else 0,
            usuario.get("equipe")
        ))

    for nome_eq, equipe in equipes.items():
        cur.execute("""
            INSERT OR IGNORE INTO equipes (nome, login, senha)
            VALUES (?, ?, ?)
        """, (
            nome_eq,
            equipe.get("login", ""),
            equipe.get("senha", "")
        ))

        for atleta in equipe.get("atletas", []):
            cpf = "".join(ch for ch in str(atleta.get("cpf", "")) if ch.isdigit())
            if not cpf:
                continue

            cur.execute("""
                INSERT OR IGNORE INTO atletas (
                    equipe_nome, nome, numero, cpf, data_nascimento, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                nome_eq,
                atleta.get("nome", ""),
                atleta.get("numero", ""),
                cpf,
                atleta.get("data_nascimento", ""),
                atleta.get("status", "pendente")
            ))

    conn.commit()
    conn.close()

    criar_admin_padrao()