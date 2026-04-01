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
            },
            "org1": {
                "nome": "Organizador 1",
                "senha": "123",
                "perfil": "organizador",
                "ativo": True,
                "equipe": None
            },
            "mesa1": {
                "nome": "Mesário 1",
                "senha": "123",
                "perfil": "mesario",
                "ativo": True,
                "equipe": None
            },
            "time1": {
                "nome": "Equipe Exemplo",
                "senha": "123",
                "perfil": "equipe",
                "ativo": True,
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

    # normaliza usuários antigos
    for login, usuario in dados["usuarios"].items():
        if "nome" not in usuario:
            usuario["nome"] = login
        if "ativo" not in usuario:
            usuario["ativo"] = True
        if "equipe" not in usuario:
            usuario["equipe"] = None

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


def nome_usuario_atual():
    return session.get("usuario")


def exige_login():
    if not usuario_logado():
        return False
    return True


def exige_perfil(perfis_permitidos):
    return perfil_atual() in perfis_permitidos


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

        if usuario in usuarios:
            usuario_dados = usuarios[usuario]

            if not usuario_dados.get("ativo", True):
                erro = "Usuário inativo."
            elif usuario_dados.get("senha") == senha:
                session["usuario"] = usuario
                session["perfil"] = usuario_dados.get("perfil")
                session["equipe"] = usuario_dados.get("equipe")
                return redirect(url_for("index"))
            else:
                erro = "Login ou senha inválidos."
        else:
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
    if not exige_login():
        return redirect(url_for("login"))

    return render_template("index.html")


# =========================================================
# MINHA CONTA - SUPERADMIN
# =========================================================
@app.route("/minha-conta", methods=["GET", "POST"])
def minha_conta():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    dados = carregar_dados()
    login_atual = nome_usuario_atual()
    usuario = dados["usuarios"].get(login_atual)

    erro_login = None
    sucesso_login = None
    erro_senha = None
    sucesso_senha = None

    if not usuario:
        return redirect(url_for("logout"))

    if request.method == "POST":
        acao = request.form.get("acao", "").strip()

        if acao == "alterar_login":
            novo_login = request.form.get("novo_login", "").strip()
            senha_atual = request.form.get("senha_atual_login", "").strip()

            if not novo_login:
                erro_login = "O novo login é obrigatório."
            elif senha_atual != usuario.get("senha"):
                erro_login = "Senha atual incorreta."
            elif novo_login == login_atual:
                erro_login = "O novo login não pode ser igual ao atual."
            elif novo_login in dados["usuarios"]:
                erro_login = "Esse login já existe."
            else:
                dados["usuarios"][novo_login] = dados["usuarios"].pop(login_atual)

                # se por algum motivo esse usuário estiver vinculado a uma equipe,
                # atualiza o login dentro da equipe também
                nome_eq = dados["usuarios"][novo_login].get("equipe")
                if nome_eq and nome_eq in dados["equipes"]:
                    dados["equipes"][nome_eq]["login"] = novo_login

                salvar_dados(dados)

                session["usuario"] = novo_login
                login_atual = novo_login
                usuario = dados["usuarios"][novo_login]

                sucesso_login = "Login alterado com sucesso."

        elif acao == "alterar_senha":
            senha_atual = request.form.get("senha_atual", "").strip()
            nova_senha = request.form.get("nova_senha", "").strip()
            confirmar_nova_senha = request.form.get("confirmar_nova_senha", "").strip()

            if senha_atual != usuario.get("senha"):
                erro_senha = "Senha atual incorreta."
            elif not nova_senha:
                erro_senha = "A nova senha é obrigatória."
            elif nova_senha != confirmar_nova_senha:
                erro_senha = "A confirmação da nova senha não confere."
            else:
                dados["usuarios"][login_atual]["senha"] = nova_senha

                nome_eq = dados["usuarios"][login_atual].get("equipe")
                if nome_eq and nome_eq in dados["equipes"]:
                    dados["equipes"][nome_eq]["senha"] = nova_senha

                salvar_dados(dados)
                sucesso_senha = "Senha alterada com sucesso."

    return render_template(
        "minha_conta.html",
        login_atual=login_atual,
        usuario=usuario,
        erro_login=erro_login,
        sucesso_login=sucesso_login,
        erro_senha=erro_senha,
        sucesso_senha=sucesso_senha
    )


# =========================================================
# USUÁRIOS - SUPERADMIN
# =========================================================
@app.route("/usuarios")
def usuarios():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    dados = carregar_dados()
    return render_template("usuarios.html", usuarios=dados["usuarios"])


@app.route("/usuarios/novo", methods=["GET", "POST"])
def novo_usuario():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    erro = None
    sucesso = None

    if request.method == "POST":
        dados = carregar_dados()

        nome = request.form.get("nome", "").strip()
        login = request.form.get("login", "").strip()
        senha = request.form.get("senha", "").strip()
        perfil = request.form.get("perfil", "").strip()
        ativo = request.form.get("ativo") == "on"

        perfis_validos = ["superadmin", "organizador", "mesario", "equipe"]

        if not nome or not login or not senha or not perfil:
            erro = "Preenche todos os campos obrigatórios."
        elif perfil not in perfis_validos:
            erro = "Perfil inválido."
        elif login in dados["usuarios"]:
            erro = "Já existe um usuário com esse login."
        else:
            dados["usuarios"][login] = {
                "nome": nome,
                "senha": senha,
                "perfil": perfil,
                "ativo": ativo,
                "equipe": None
            }
            salvar_dados(dados)
            sucesso = "Usuário criado com sucesso."

    return render_template("novo_usuario.html", erro=erro, sucesso=sucesso)


@app.route("/usuarios/editar/<login_usuario>", methods=["GET", "POST"])
def editar_usuario(login_usuario):
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    dados = carregar_dados()

    if login_usuario not in dados["usuarios"]:
        return redirect(url_for("usuarios"))

    usuario = dados["usuarios"][login_usuario]
    erro = None
    sucesso = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        senha = request.form.get("senha", "").strip()
        perfil = request.form.get("perfil", "").strip()
        ativo = request.form.get("ativo") == "on"

        perfis_validos = ["superadmin", "organizador", "mesario", "equipe"]

        if not nome or not perfil:
            erro = "Nome e perfil são obrigatórios."
        elif perfil not in perfis_validos:
            erro = "Perfil inválido."
        else:
            usuario["nome"] = nome
            usuario["perfil"] = perfil
            usuario["ativo"] = ativo

            if senha:
                usuario["senha"] = senha
                nome_eq = usuario.get("equipe")
                if nome_eq and nome_eq in dados["equipes"]:
                    dados["equipes"][nome_eq]["senha"] = senha

            salvar_dados(dados)
            sucesso = "Usuário atualizado com sucesso."

    return render_template(
        "editar_usuario.html",
        login_usuario=login_usuario,
        usuario=usuario,
        erro=erro,
        sucesso=sucesso
    )


# =========================================================
# EQUIPES - ORGANIZADOR / SUPERADMIN
# =========================================================
@app.route("/equipes")
def equipes():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    dados = carregar_dados()
    lista_equipes = dados.get("equipes", {})
    return render_template("equipes.html", equipes=lista_equipes)


@app.route("/equipes/nova", methods=["GET", "POST"])
def nova_equipe():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
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
            "nome": nome_equipe,
            "senha": senha_gerada,
            "perfil": "equipe",
            "ativo": True,
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
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "mesario"]):
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Tabela")


@app.route("/pre-jogo")
def pre_jogo():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "mesario"]):
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Pré-jogo")


@app.route("/jogo")
def jogo():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "mesario"]):
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Jogo")


# =========================================================
# PORTAL DA EQUIPE
# =========================================================
@app.route("/meu-time", methods=["GET", "POST"])
def meu_time():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["equipe"]):
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
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    return render_template("pagina_simples.html", titulo="Competições")


# =========================================================
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)