from flask import Flask, render_template, request, redirect, session
from functools import wraps

app = Flask(__name__)
app.secret_key = "super_secreto"

# =========================
# USUÁRIOS (temporário)
# =========================
USUARIOS = {
    "admin": {"senha": "admin123", "perfil": "admin"},
    "organizador": {"senha": "org123", "perfil": "organizador"},
    "mesario": {"senha": "mesa123", "perfil": "mesario"},
    "equipe": {"senha": "equipe123", "perfil": "equipe"},
}

# =========================
# PROTEÇÕES
# =========================
def login_obrigatorio(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "usuario" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


def perfil_obrigatorio(perfis):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get("perfil") not in perfis:
                return "Acesso negado", 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# =========================
# ROTAS
# =========================
@app.route("/")
@login_obrigatorio
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        if usuario in USUARIOS and USUARIOS[usuario]["senha"] == senha:
            session["usuario"] = usuario
            session["perfil"] = USUARIOS[usuario]["perfil"]
            return redirect("/")

        return render_template("login.html", erro="Login inválido")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# EXEMPLOS DE PERMISSÃO
# =========================
@app.route("/competicoes")
@login_obrigatorio
@perfil_obrigatorio(["admin", "organizador"])
def competicoes():
    return "Área de Competições"


@app.route("/jogo")
@login_obrigatorio
@perfil_obrigatorio(["admin", "mesario"])
def jogo():
    return "Área do Jogo"


@app.route("/minha-equipe")
@login_obrigatorio
@perfil_obrigatorio(["equipe"])
def equipe():
    return "Área da Equipe"


if __name__ == "__main__":
    app.run(debug=True)