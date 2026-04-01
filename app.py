from flask import Flask, render_template, request, redirect, session, url_for
import os

app = Flask(__name__)
app.secret_key = "voleibol123"

# =========================================================
# USUÁRIOS DE TESTE
# =========================================================
# Mantém simples por enquanto, só para estabilizar o login.
# Depois a gente troca para usuários vindos de JSON ou banco.
usuarios = {
    "admin": {
        "senha": "123",
        "perfil": "superadmin"
    },
    "org1": {
        "senha": "123",
        "perfil": "organizador"
    },
    "mesa1": {
        "senha": "123",
        "perfil": "mesario"
    },
    "time1": {
        "senha": "123",
        "perfil": "equipe"
    }
}


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def usuario_logado():
    return "usuario" in session


def perfil_atual():
    return session.get("perfil")


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

        if usuario in usuarios and usuarios[usuario]["senha"] == senha:
            session["usuario"] = usuario
            session["perfil"] = usuarios[usuario]["perfil"]
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
# ROTAS POR PERFIL
# =========================================================
@app.route("/competicoes")
def competicoes():
    if not usuario_logado():
        return redirect(url_for("login"))

    if perfil_atual() not in ["superadmin", "organizador"]:
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Competições")


@app.route("/equipes")
def equipes():
    if not usuario_logado():
        return redirect(url_for("login"))

    if perfil_atual() not in ["superadmin", "organizador"]:
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Equipes")


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


@app.route("/meu-time")
def meu_time():
    if not usuario_logado():
        return redirect(url_for("login"))

    if perfil_atual() != "equipe":
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Meu Time")


# =========================================================
# EXECUÇÃO LOCAL / RENDER
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    app.run(host="0.0.0.0", port=port)