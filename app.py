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
                "senha": "123",
                "perfil": "superadmin",
                "equipe": None
            },
            "org1": {
                "senha": "123",
                "perfil": "organizador",
                "equipe": None
            },
            "mesa1": {
                "senha": "123",
                "perfil": "mesario",
                "equipe": None
            },
            "time1": {
                "senha": "123",
                "perfil": "equipe",
                "equipe": "Equipe Exemplo"
            }
        },
        "equipes": {
            "Equipe Exemplo": {
                "nome": "Equipe Exemplo",
                "login": "time1",
                "senha": "123",
                "atletas": []
            }
        }
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
        dados = dados_padrao()
        salvar_dados(dados)
        return dados

    if "usuarios" not in dados or not isinstance(dados["usuarios"], dict):
        dados["usuarios"] = {}
    if "equipes" not in dados or not isinstance(dados["equipes"], dict):
        dados["equipes"] = {}

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


def gerar_login_equipe(nome_equipe, usuarios_existentes):
    base = nome_equipe.strip().lower()
    caracteres_invalidos = ".,;:/\\|!?@#$%¨&*()[]{}=+´`~^'\""
    for c in caracteres_invalidos:
        base = base.replace(c, "")
    base = base.replace("-", " ")
    base = "_".join(base.split())

    if not base:
        base = "equipe"

    login = base
    contador = 1

    while login in usuarios_existentes:
        login = f"{base}_{contador}"
        contador += 1

    return login


def gerar_senha_automatica(tamanho=7):
    caracteres = string.ascii_letters + string.digits
    return "".join(random.choice(caracteres) for _ in range(tamanho))


# =========================================================
# LOGIN
# =========================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if usuario_logado():
        return redirect(url_for("index"))

    erro = None

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "").strip()

        dados = carregar_dados()
        usuarios = dados.get("usuarios", {})

        if usuario in usuarios and usuarios[usuario]["senha"] == senha:
            session["usuario"] = usuario
            session["perfil"] = usuarios[usuario]["perfil"]
            session["equipe"] = usuarios[usuario].get("equipe")
            return redirect(url_for("index"))

        erro = "Login ou senha inválidos."

    return render_template("login.html", erro=erro)


# =========================================================
# LOGOUT
# =========================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================================================
# PÁGINA INICIAL
# =========================================================
@app.route("/")
def index():
    if not usuario_logado():
        return redirect(url_for("login"))

    return render_template("index.html")


# =========================================================
# EQUIPES - ORGANIZADOR / SUPERADMIN
# =========================================================
@app.route("/equipes")
def equipes():
    if not usuario_logado():
        return redirect(url_for("login"))

    if perfil_atual() not in ["superadmin", "organizador"]:
        return redirect(url_for("index"))

    dados = carregar_dados()
    lista_equipes = dados.get("equipes", {})
    return render_template("equipes.html", equipes=lista_equipes)


@app.route("/equipes/nova", methods=["GET", "POST"])
def nova_equipe():
    if not usuario_logado():
        return redirect(url_for("login"))

    if perfil_atual() not in ["superadmin", "organizador"]:
        return redirect(url_for("index"))

    erro = None
    sucesso = None
    dados_gerados = None

    if request.method == "POST":
        nome_equipe = request.form.get("nome_equipe", "").strip()

        if not nome_equipe:
            erro = "O nome da equipe é obrigatório."
            return render_template(
                "nova_equipe.html",
                erro=erro,
                sucesso=sucesso,
                dados_gerados=dados_gerados
            )

        dados = carregar_dados()

        if nome_equipe in dados["equipes"]:
            erro = "Já existe uma equipe com esse nome."
            return render_template(
                "nova_equipe.html",
                erro=erro,
                sucesso=sucesso,
                dados_gerados=dados_gerados
            )

        login_gerado = gerar_login_equipe(nome_equipe, dados["usuarios"])
        senha_gerada = gerar_senha_automatica()

        dados["equipes"][nome_equipe] = {
            "nome": nome_equipe,
            "login": login_gerado,
            "senha": senha_gerada,
            "atletas": []
        }

        dados["usuarios"][login_gerado] = {
            "senha": senha_gerada,
            "perfil": "equipe",
            "equipe": nome_equipe
        }

        salvar_dados(dados)

        sucesso = "Equipe criada com sucesso."
        dados_gerados = {
            "nome_equipe": nome_equipe,
            "login": login_gerado,
            "senha": senha_gerada
        }

    return render_template(
        "nova_equipe.html",
        erro=erro,
        sucesso=sucesso,
        dados_gerados=dados_gerados
    )


# =========================================================
# TABELA / PRÉ-JOGO / JOGO - MESÁRIO / SUPERADMIN
# =========================================================
@app.route("/tabela")
def tabela():
    if not usuario_logado():
        return redirect(url_for("login"))

    if perfil_atual() not in ["superadmin", "mesario"]:
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Tabela")


@app.route("/pre-jogo")
def pre_jogo():
    if not usuario_logado():
        return redirect(url_for("login"))

    if perfil_atual() not in ["superadmin", "mesario"]:
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Pré-jogo")


@app.route("/jogo")
def jogo():
    if not usuario_logado():
        return redirect(url_for("login"))

    if perfil_atual() not in ["superadmin", "mesario"]:
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Jogo")


# =========================================================
# PORTAL DA EQUIPE
# =========================================================
@app.route("/meu-time", methods=["GET", "POST"])
def meu_time():
    if not usuario_logado():
        return redirect(url_for("login"))

    if perfil_atual() != "equipe":
        return redirect(url_for("index"))

    dados = carregar_dados()
    nome_equipe = equipe_atual()

    if not nome_equipe or nome_equipe not in dados["equipes"]:
        return redirect(url_for("logout"))

    equipe = dados["equipes"][nome_equipe]
    erro = None
    sucesso = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        numero = request.form.get("numero", "").strip()
        cpf = request.form.get("cpf", "").strip()
        data_nascimento = request.form.get("data_nascimento", "").strip()

        if not nome or not cpf or not data_nascimento:
            erro = "Nome, CPF e data de nascimento são obrigatórios."
        else:
            equipe["atletas"].append({
                "nome": nome,
                "numero": numero,
                "cpf": cpf,
                "data_nascimento": data_nascimento,
                "status": "pendente"
            })
            salvar_dados(dados)
            sucesso = "Atleta cadastrado com sucesso."

    return render_template(
        "meu_time.html",
        equipe=equipe,
        erro=erro,
        sucesso=sucesso
    )


# =========================================================
# COMPETIÇÕES - mantém a rota sem quebrar menu
# =========================================================
@app.route("/competicoes")
def competicoes():
    if not usuario_logado():
        return redirect(url_for("login"))

    if perfil_atual() not in ["superadmin", "organizador"]:
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Competições")


# =========================================================
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)