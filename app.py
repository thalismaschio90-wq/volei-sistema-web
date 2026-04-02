from flask import Flask, render_template, request, redirect, session, url_for
import os
import json
import random
import string
from pathlib import Path

app = Flask(__name__)
app.secret_key = "voleibol123"

ARQUIVO_DADOS = Path("dados.json")


# =========================================================
# DADOS
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
        "equipes": {}
    }


def carregar_dados():
    if not ARQUIVO_DADOS.exists():
        dados = dados_padrao()
        salvar_dados(dados)
        return dados

    try:
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return dados_padrao()

    if "usuarios" not in dados or not isinstance(dados["usuarios"], dict):
        dados["usuarios"] = {}

    if "equipes" not in dados or not isinstance(dados["equipes"], dict):
        dados["equipes"] = {}

    # normalização segura
    for login, usuario in dados["usuarios"].items():
        usuario.setdefault("nome", login)
        usuario.setdefault("ativo", True)
        usuario.setdefault("equipe", None)

    for nome_eq, equipe in dados["equipes"].items():
        equipe.setdefault("nome", nome_eq)
        equipe.setdefault("login", "")
        equipe.setdefault("senha", "")
        equipe.setdefault("atletas", [])

        for atleta in equipe["atletas"]:
            atleta.setdefault("nome", "")
            atleta.setdefault("numero", "")
            atleta.setdefault("cpf", "")
            atleta.setdefault("data_nascimento", "")
            atleta.setdefault("status", "pendente")

    return dados


def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def usuario_logado():
    return "usuario" in session


def perfil_atual():
    return session.get("perfil")


def equipe_atual():
    return session.get("equipe")


def exige_login():
    return usuario_logado()


def exige_perfil(perfis):
    return perfil_atual() in perfis


def gerar_login_equipe(nome, usuarios):
    base = "_".join(nome.lower().split())
    login = base
    i = 1
    while login in usuarios:
        login = f"{base}_{i}"
        i += 1
    return login


def gerar_senha():
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(6))


# =========================================================
# LOGIN
# =========================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if usuario_logado():
        return redirect(url_for("index"))

    erro = None

    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        dados = carregar_dados()

        if usuario in dados["usuarios"]:
            u = dados["usuarios"][usuario]

            if not u["ativo"]:
                erro = "Usuário inativo."
            elif u["senha"] == senha:
                session["usuario"] = usuario
                session["perfil"] = u["perfil"]
                session["equipe"] = u["equipe"]
                return redirect(url_for("index"))
            else:
                erro = "Senha inválida."
        else:
            erro = "Usuário não encontrado."

    return render_template("login.html", erro=erro)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================================================
# HOME
# =========================================================
@app.route("/")
def index():
    if not exige_login():
        return redirect(url_for("login"))
    return render_template("index.html")


# =========================================================
# EQUIPES
# =========================================================
@app.route("/equipes")
def equipes():
    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    dados = carregar_dados()
    return render_template("equipes.html", equipes=dados["equipes"])


@app.route("/equipes/nova", methods=["GET", "POST"])
def nova_equipe():
    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    erro = None
    sucesso = None
    dados_gerados = None

    if request.method == "POST":
        nome = request.form.get("nome_equipe")

        dados = carregar_dados()

        if nome in dados["equipes"]:
            erro = "Equipe já existe."
        else:
            login = gerar_login_equipe(nome, dados["usuarios"])
            senha = gerar_senha()

            dados["equipes"][nome] = {
                "nome": nome,
                "login": login,
                "senha": senha,
                "atletas": []
            }

            dados["usuarios"][login] = {
                "nome": nome,
                "senha": senha,
                "perfil": "equipe",
                "ativo": True,
                "equipe": nome
            }

            salvar_dados(dados)

            sucesso = "Equipe criada."
            dados_gerados = {"login": login, "senha": senha}

    return render_template("nova_equipe.html", erro=erro, sucesso=sucesso, dados_gerados=dados_gerados)


# =========================================================
# MEU TIME
# =========================================================
@app.route("/meu-time", methods=["GET", "POST"])
def meu_time():
    if not exige_perfil(["equipe"]):
        return redirect(url_for("index"))

    dados = carregar_dados()
    nome = equipe_atual()
    equipe = dados["equipes"][nome]

    erro = None
    sucesso = None

    if request.method == "POST":
        acao = request.form.get("acao")

        if acao == "excluir":
            cpf = request.form.get("cpf")
            equipe["atletas"] = [a for a in equipe["atletas"] if a["cpf"] != cpf]
            salvar_dados(dados)
            sucesso = "Excluído."

        else:
            atleta = {
                "nome": request.form.get("nome"),
                "numero": request.form.get("numero"),
                "cpf": request.form.get("cpf"),
                "data_nascimento": request.form.get("data_nascimento"),
                "status": "pendente"
            }

            equipe["atletas"].append(atleta)
            salvar_dados(dados)
            sucesso = "Cadastrado."

    return render_template("meu_time.html", equipe=equipe, erro=erro, sucesso=sucesso)


# =========================================================
# APROVAÇÕES
# =========================================================
@app.route("/aprovacoes", methods=["GET", "POST"])
def aprovacoes():
    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    dados = carregar_dados()

    if request.method == "POST":
        eq = request.form.get("equipe")
        cpf = request.form.get("cpf")
        acao = request.form.get("acao")

        for atleta in dados["equipes"][eq]["atletas"]:
            if atleta["cpf"] == cpf:
                atleta["status"] = "aprovado" if acao == "aprovar" else "rejeitado"

        salvar_dados(dados)

    return render_template("aprovacoes.html", equipes=dados["equipes"])


# =========================================================
# LISTAGEM OFICIAL
# =========================================================
@app.route("/listagem-oficial")
def listagem_oficial():
    dados = carregar_dados()

    filtrado = {}

    for nome, eq in dados["equipes"].items():
        aprovados = [a for a in eq["atletas"] if a["status"] == "aprovado"]
        if aprovados:
            filtrado[nome] = {"atletas": aprovados}

    return render_template("listagem_oficial.html", equipes=filtrado)


# =========================================================
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)