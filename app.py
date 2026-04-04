from flask import Flask, render_template, request, redirect, session, url_for
import os
import random
import string

from banco import obter_dados, salvar_dados, inicializar_banco

app = Flask(__name__)
app.secret_key = "voleibol123"


# =========================================================
# AUXILIARES
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


def gerar_login_equipe(nome, usuarios):
    base = nome.lower().replace(" ", "_")
    login = base
    i = 1
    while login in usuarios:
        login = f"{base}_{i}"
        i += 1
    return login


def gerar_senha():
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
# MINHA CONTA
# =========================================================
@app.route("/minha-conta")
def minha_conta():
    if not exige_login():
        return redirect(url_for("login"))

    return render_template("minha_conta.html")


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

        nome = request.form.get("nome")
        login = request.form.get("login")
        senha = request.form.get("senha")
        perfil = request.form.get("perfil")

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
            sucesso = "Usuário criado com sucesso"

    return render_template("novo_usuario.html", erro=erro, sucesso=sucesso)


# =========================================================
# EDITAR USUÁRIO (CORREÇÃO DO ERRO 500)
# =========================================================
@app.route("/usuarios/editar/<login_usuario>", methods=["GET", "POST"])
def editar_usuario(login_usuario):
    if not exige_login() or not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    dados = obter_dados()

    if login_usuario not in dados["usuarios"]:
        return redirect(url_for("usuarios"))

    usuario = dados["usuarios"][login_usuario]
    erro = None
    sucesso = None

    if request.method == "POST":
        nome = request.form.get("nome")
        senha = request.form.get("senha")
        perfil = request.form.get("perfil")
        ativo = request.form.get("ativo") == "on"

        usuario["nome"] = nome
        usuario["perfil"] = perfil
        usuario["ativo"] = ativo

        if senha:
            usuario["senha"] = senha

        salvar_dados(dados)
        sucesso = "Usuário atualizado"

    return render_template(
        "editar_usuario.html",
        usuario=usuario,
        login_usuario=login_usuario,
        erro=erro,
        sucesso=sucesso
    )


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
        nome = request.form.get("nome_equipe")

        if nome in dados["equipes"]:
            erro = "Equipe já existe"
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

            sucesso = "Equipe criada"
            dados_gerados = {
                "nome_equipe": nome,
                "login": login,
                "senha": senha
            }

    return render_template(
        "nova_equipe.html",
        erro=erro,
        sucesso=sucesso,
        dados_gerados=dados_gerados
    )


# =========================================================
# APROVAÇÕES
# =========================================================
@app.route("/aprovacoes")
def aprovacoes():
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()
    return render_template("aprovacoes.html", equipes=dados.get("equipes", {}))


# =========================================================
# LISTAGEM OFICIAL
# =========================================================
@app.route("/listagem-oficial")
def listagem_oficial():
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()
    equipes_filtradas = {}

    for nome_eq, equipe in dados.get("equipes", {}).items():
        atletas_aprovados = [
            a for a in equipe.get("atletas", [])
            if a.get("status") == "aprovado"
        ]

        if atletas_aprovados:
            equipes_filtradas[nome_eq] = {
                "nome": nome_eq,
                "atletas": atletas_aprovados
            }

    return render_template("listagem_oficial.html", equipes=equipes_filtradas)


# =========================================================
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    inicializar_banco()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)