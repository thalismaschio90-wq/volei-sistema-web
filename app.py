from flask import Flask, render_template, request, redirect, session, url_for
import os
import random
import string

from banco import obter_dados, salvar_dados, inicializar_banco

app = Flask(__name__)
app.secret_key = "voleibol123"


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def usuario_logado():
    return "usuario" in session


def perfil_atual():
    return session.get("perfil")


def equipe_atual():
    return session.get("equipe")


def nome_usuario_atual():
    return session.get("usuario")


def exige_login():
    return usuario_logado()


def exige_perfil(perfis):
    return perfil_atual() in perfis


def gerar_login_equipe(nome_equipe, usuarios_existentes):
    base = nome_equipe.lower().replace(" ", "_")
    login = base
    i = 1
    while login in usuarios_existentes:
        login = f"{base}_{i}"
        i += 1
    return login


def gerar_senha_automatica():
    return "".join(random.choices(string.ascii_letters + string.digits, k=6))


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

        dados = obter_dados()

        if usuario in dados["usuarios"]:
            u = dados["usuarios"][usuario]

            if not u.get("ativo", True):
                erro = "Usuário inativo"
            elif u["senha"] == senha:
                session["usuario"] = usuario
                session["perfil"] = u["perfil"]
                session["equipe"] = u.get("equipe")
                return redirect(url_for("index"))
            else:
                erro = "Senha incorreta"
        else:
            erro = "Usuário não encontrado"

    return render_template("login.html", erro=erro)


# =========================================================
# LOGOUT
# =========================================================
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
# USUÁRIOS
# =========================================================
@app.route("/usuarios")
def usuarios():
    if not exige_login() or not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    dados = obter_dados()
    return render_template("usuarios.html", usuarios=dados["usuarios"])


@app.route("/usuarios/novo", methods=["GET", "POST"])
def novo_usuario():
    if not exige_login() or not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    erro = None
    sucesso = None

    if request.method == "POST":
        dados = obter_dados()

        nome = request.form["nome"]
        login = request.form["login"]
        senha = request.form["senha"]
        perfil = request.form["perfil"]

        if login in dados["usuarios"]:
            erro = "Login já existe"
        else:
            dados["usuarios"][login] = {
                "nome": nome,
                "senha": senha,
                "perfil": perfil,
                "ativo": True,
                "equipe": None
            }
            salvar_dados(dados)
            sucesso = "Criado com sucesso"

    return render_template("novo_usuario.html", erro=erro, sucesso=sucesso)


# =========================================================
# EQUIPES
# =========================================================
@app.route("/equipes")
def equipes():
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()
    return render_template("equipes.html", equipes=dados.get("equipes", {}))


@app.route("/equipes/nova", methods=["GET", "POST"])
def nova_equipe():
    if not exige_login():
        return redirect(url_for("login"))

    erro = None
    sucesso = None
    dados_gerados = None

    if request.method == "POST":
        dados = obter_dados()
        nome = request.form["nome_equipe"]

        if nome in dados["equipes"]:
            erro = "Equipe já existe"
        else:
            login = gerar_login_equipe(nome, dados["usuarios"])
            senha = gerar_senha_automatica()

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

            sucesso = "Equipe criada"
            dados_gerados = {"nome_equipe": nome, "login": login, "senha": senha}

    return render_template("nova_equipe.html", erro=erro, sucesso=sucesso, dados_gerados=dados_gerados)


# =========================================================
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    inicializar_banco()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)