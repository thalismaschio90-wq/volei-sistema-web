from flask import Flask, render_template, request, redirect, url_for, flash
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_DADOS = BASE_DIR / "dados_volei.json"

app = Flask(__name__)
app.secret_key = "volleytable-pro-web-step2"


def carregar_dados():
    if not ARQUIVO_DADOS.exists():
        return {"competicoes": {}}

    try:
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return {"competicoes": {}}

    if not isinstance(dados, dict):
        return {"competicoes": {}}

    if "competicoes" not in dados or not isinstance(dados["competicoes"], dict):
        dados["competicoes"] = {}

    return dados


def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


@app.route("/")
def index():
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
    )


@app.route("/competicoes")
def competicoes():
    dados = carregar_dados()
    competicoes = dados.get("competicoes", {})
    return render_template("competicoes.html", competicoes=competicoes)


@app.route("/competicoes/nova", methods=["GET", "POST"])
def nova_competicao():
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
    app.run(debug=True)
