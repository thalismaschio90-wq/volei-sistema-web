from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_DADOS = BASE_DIR / "dados_volei.json"

app = Flask(__name__)
app.secret_key = "volleytable-pro-login-step3"


def carregar_dados():
    if not ARQUIVO_DADOS.exists():
        return {"competicoes": {}, "usuarios": {}}

    try:
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return {"competicoes": {}, "usuarios": {}}

    if not isinstance(dados, dict):
        return {"competicoes": {}, "usuarios": {}}

    if "competicoes" not in dados or not isinstance(dados["competicoes"], dict):
        dados["competicoes"] = {}

    if "usuarios" not in dados or not isinstance(dados["usuarios"], dict):
        dados["usuarios"] = {}

    return dados


def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


def usuario_logado():
    return session.get("usuario")


def perfil_logado():
    return session.get("perfil")


def login_obrigatorio():
    return usuario_logado() is not None


@app.route("/login", methods=["GET", "POST"])
def login():
    if login_obrigatorio():
        return redirect(url_for("index"))

    if request.method == "POST":
        login_digitado = request.form.get("login", "").strip()
        senha_digitada = request.form.get("senha", "").strip()

        dados = carregar_dados()
        usuarios = dados.get("usuarios", {})
        usuario = usuarios.get(login_digitado)

        if not usuario:
            flash("Login não encontrado.", "erro")
            return render_template("login.html")

        if usuario.get("senha") != senha_digitada:
            flash("Senha inválida.", "erro")
            return render_template("login.html")

        session["usuario"] = login_digitado
        session["perfil"] = usuario.get("perfil", "visualizador")
        session["nome_exibicao"] = usuario.get("nome", login_digitado)

        flash(f"Bem-vindo, {usuario.get('nome', login_digitado)}.", "sucesso")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sessão encerrada com sucesso.", "sucesso")
    return redirect(url_for("login"))


@app.route("/")
def index():
    if not login_obrigatorio():
        return redirect(url_for("login"))

    dados = carregar_dados()
    competicoes = dados.get("competicoes", {})

    total_competicoes = len(competicoes)
    total_equipes = 0
    total_partidas = 0

    for comp in competicoes.values():
        equipes = comp.get("equipes", {})
        partidas = comp.get("partidas", {})
        if isinstance(equipes, dict):
            total_equipes += len(equipes)
        if isinstance(partidas, dict):
            total_partidas += len(partidas)
        elif isinstance(partidas, list):
            total_partidas += len(partidas)

    return render_template(
        "index.html",
        total_competicoes=total_competicoes,
        total_equipes=total_equipes,
        total_partidas=total_partidas,
        usuario=session.get("nome_exibicao", ""),
        perfil=session.get("perfil", ""),
    )


@app.route("/competicoes")
def competicoes():
    if not login_obrigatorio():
        return redirect(url_for("login"))

    dados = carregar_dados()
    competicoes = dados.get("competicoes", {})
    return render_template("competicoes.html", competicoes=competicoes)


@app.route("/competicoes/nova", methods=["GET", "POST"])
def nova_competicao():
    if not login_obrigatorio():
        return redirect(url_for("login"))

    if perfil_logado() not in ["superadmin", "organizador"]:
        flash("Tu não tens permissão para criar competições.", "erro")
        return redirect(url_for("index"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cidade = request.form.get("cidade", "").strip()
        ginasio = request.form.get("ginasio", "").strip()
        categoria = request.form.get("categoria", "").strip()
        sexo = request.form.get("sexo", "").strip()

        if not nome:
            flash("O nome da competição é obrigatório.", "erro")
            return render_template("nova_competicao.html")

        dados = carregar_dados()
        competicoes = dados.setdefault("competicoes", {})

        if nome in competicoes:
            flash("Já existe uma competição com esse nome.", "erro")
            return render_template("nova_competicao.html")

        competicoes[nome] = {
            "dados": {
                "nome": nome,
                "cidade": cidade,
                "ginasio": ginasio,
                "categoria": categoria,
                "sexo": sexo,
            },
            "equipes": {},
            "partidas": {}
        }

        salvar_dados(dados)
        flash("Competição criada com sucesso.", "sucesso")
        return redirect(url_for("competicoes"))

    return render_template("nova_competicao.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
