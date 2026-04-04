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
    base = nome.strip().lower()
    caracteres_invalidos = ".,;:/\\|!?@#$%¨&*()[]{}=+´`~^'\""
    for c in caracteres_invalidos:
        base = base.replace(c, "")
    base = base.replace("-", " ")
    base = "_".join(base.split())

    if not base:
        base = "equipe"

    login = base
    contador = 1

    while login in usuarios:
        login = f"{base}_{contador}"
        contador += 1

    return login


def gerar_senha():
    caracteres = string.ascii_letters + string.digits
    return "".join(random.choice(caracteres) for _ in range(6))


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

        dados = obter_dados()

        if not dados:
            erro = "Erro ao carregar dados do sistema."
            return render_template("login.html", erro=erro)

        usuarios = dados.get("usuarios", {})

        if usuario in usuarios:
            u = usuarios[usuario]

            if not u.get("ativo", True):
                erro = "Usuário inativo."
            elif u.get("senha") == senha:
                session["usuario"] = usuario
                session["perfil"] = u.get("perfil")
                session["equipe"] = u.get("equipe")
                return redirect(url_for("index"))
            else:
                erro = "Senha incorreta."
        else:
            erro = "Usuário não encontrado."

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
# PAINÉIS
# =========================================================
@app.route("/painel-organizador")
def painel_organizador():
    if not exige_login():
        return redirect(url_for("login"))

    return render_template("painel_organizador.html")


@app.route("/painel-mesario")
def painel_mesario():
    if not exige_login():
        return redirect(url_for("login"))

    return render_template("painel_mesario.html")


@app.route("/painel-superadmin")
def painel_superadmin():
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()
    usuarios = dados.get("usuarios", {})
    equipes = dados.get("equipes", {})

    total_usuarios = len(usuarios)
    total_organizadores = sum(1 for u in usuarios.values() if u.get("perfil") == "organizador")
    total_mesarios = sum(1 for u in usuarios.values() if u.get("perfil") == "mesario")
    total_equipes = len(equipes)
    total_atletas = sum(len(eq.get("atletas", [])) for eq in equipes.values())
    total_aprovados = sum(
        1
        for eq in equipes.values()
        for atleta in eq.get("atletas", [])
        if atleta.get("status") == "aprovado"
    )

    resumo = {
        "total_usuarios": total_usuarios,
        "total_organizadores": total_organizadores,
        "total_mesarios": total_mesarios,
        "total_equipes": total_equipes,
        "total_atletas": total_atletas,
        "total_aprovados": total_aprovados,
    }

    return render_template("painel_superadmin.html", resumo=resumo)


# =========================================================
# MINHA CONTA
# =========================================================
@app.route("/minha-conta", methods=["GET", "POST"])
def minha_conta():
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()
    login_atual = nome_usuario_atual()
    usuario = dados.get("usuarios", {}).get(login_atual)

    if not usuario:
        return redirect(url_for("logout"))

    erro_login = None
    sucesso_login = None
    erro_senha = None
    sucesso_senha = None

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

                # se o usuário estiver vinculado a equipe, atualiza o login da equipe também
                nome_eq = dados["usuarios"][novo_login].get("equipe")
                if nome_eq and nome_eq in dados.get("equipes", {}):
                    dados["equipes"][nome_eq]["login"] = novo_login

                salvar_dados(dados)

                session["usuario"] = novo_login
                login_atual = novo_login
                usuario = dados["usuarios"][novo_login]

                sucesso_login = "Login alterado com sucesso."

        elif acao == "alterar_senha":
            senha_atual = request.form.get("senha_atual", "").strip()
            nova_senha = request.form.get("nova_senha", "").strip()
            confirmar = request.form.get("confirmar_nova_senha", "").strip()

            if senha_atual != usuario.get("senha"):
                erro_senha = "Senha atual incorreta."
            elif not nova_senha:
                erro_senha = "A nova senha é obrigatória."
            elif nova_senha != confirmar:
                erro_senha = "A confirmação da nova senha não confere."
            else:
                dados["usuarios"][login_atual]["senha"] = nova_senha

                nome_eq = dados["usuarios"][login_atual].get("equipe")
                if nome_eq and nome_eq in dados.get("equipes", {}):
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
# USUÁRIOS
# =========================================================
@app.route("/usuarios")
def usuarios():
    if not exige_login():
        return redirect(url_for("login"))

    # mantive como já vinha funcionando para superadmin
    dados = obter_dados()
    return render_template("usuarios.html", usuarios=dados.get("usuarios", {}))


@app.route("/usuarios/novo", methods=["GET", "POST"])
def novo_usuario():
    if not exige_login():
        return redirect(url_for("login"))

    erro = None
    sucesso = None

    if request.method == "POST":
        dados = obter_dados()

        nome = request.form.get("nome", "").strip()
        login = request.form.get("login", "").strip()
        senha = request.form.get("senha", "").strip()
        perfil = request.form.get("perfil", "").strip()
        ativo = request.form.get("ativo") == "on"
        acesso_ate = request.form.get("acesso_ate", "").strip()

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
                "equipe": None,
                "acesso_ate": acesso_ate if perfil == "organizador" else ""
            }

            salvar_dados(dados)
            sucesso = "Usuário criado com sucesso."

    return render_template("novo_usuario.html", erro=erro, sucesso=sucesso)


@app.route("/usuarios/editar/<login_usuario>", methods=["GET", "POST"])
def editar_usuario(login_usuario):
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()

    if login_usuario not in dados.get("usuarios", {}):
        return redirect(url_for("usuarios"))

    usuario = dados["usuarios"][login_usuario]
    erro = None
    sucesso = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        senha = request.form.get("senha", "").strip()
        perfil = request.form.get("perfil", "").strip()
        ativo = request.form.get("ativo") == "on"
        acesso_ate = request.form.get("acesso_ate", "").strip()

        perfis_validos = ["superadmin", "organizador", "mesario", "equipe"]

        if not nome or not perfil:
            erro = "Nome e perfil são obrigatórios."
        elif perfil not in perfis_validos:
            erro = "Perfil inválido."
        else:
            usuario["nome"] = nome
            usuario["perfil"] = perfil
            usuario["ativo"] = ativo
            usuario["acesso_ate"] = acesso_ate if perfil == "organizador" else ""

            if senha:
                usuario["senha"] = senha

            salvar_dados(dados)
            sucesso = "Usuário atualizado."

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
        nome = request.form.get("nome_equipe", "").strip()

        if not nome:
            erro = "O nome da equipe é obrigatório."
        elif nome in dados.get("equipes", {}):
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
                "equipe": nome,
                "acesso_ate": ""
            }

            salvar_dados(dados)

            sucesso = "Equipe criada."
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
# MEU TIME
# =========================================================
@app.route("/meu-time", methods=["GET", "POST"])
def meu_time():
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()
    nome_equipe = equipe_atual()

    if not nome_equipe or nome_equipe not in dados.get("equipes", {}):
        return redirect(url_for("logout"))

    equipe = dados["equipes"][nome_equipe]
    erro = None
    sucesso = None

    configuracoes = dados.get("configuracoes", {})
    prazo_cadastro = configuracoes.get("prazo_cadastro_atletas", "")
    prazo_edicao = configuracoes.get("prazo_edicao_atletas", "")

    cadastro_bloqueado = False
    edicao_bloqueada = False

    if request.method == "POST":
        acao = request.form.get("acao", "").strip()

        if acao == "excluir":
            cpf = request.form.get("cpf", "").strip()
            indice_remover = None

            for i, atleta in enumerate(equipe.get("atletas", [])):
                if atleta.get("cpf") == cpf:
                    indice_remover = i
                    break

            if indice_remover is not None:
                equipe["atletas"].pop(indice_remover)
                salvar_dados(dados)
                sucesso = "Atleta excluído com sucesso."
            else:
                erro = "Atleta não encontrado para exclusão."

        else:
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
        sucesso=sucesso,
        prazo_cadastro=prazo_cadastro,
        prazo_edicao=prazo_edicao,
        cadastro_bloqueado=cadastro_bloqueado,
        edicao_bloqueada=edicao_bloqueada
    )


# =========================================================
# APROVAÇÕES
# =========================================================
@app.route("/aprovacoes", methods=["GET", "POST"])
def aprovacoes():
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()
    sucesso = None
    erro = None

    if request.method == "POST":
        acao = request.form.get("acao", "").strip()
        equipe_nome = request.form.get("equipe", "").strip()
        cpf = request.form.get("cpf", "").strip()

        if equipe_nome in dados.get("equipes", {}):
            atletas = dados["equipes"][equipe_nome].get("atletas", [])

            if acao in ["aprovar", "rejeitar"]:
                for atleta in atletas:
                    if atleta.get("cpf") == cpf:
                        atleta["status"] = "aprovado" if acao == "aprovar" else "rejeitado"
                        sucesso = f"Atleta {atleta['status']} com sucesso."
                        break
                salvar_dados(dados)

            elif acao == "excluir":
                indice_remover = None
                for i, atleta in enumerate(atletas):
                    if atleta.get("cpf") == cpf:
                        indice_remover = i
                        break

                if indice_remover is not None:
                    atletas.pop(indice_remover)
                    salvar_dados(dados)
                    sucesso = "Atleta excluído com sucesso."
                else:
                    erro = "Atleta não encontrado para exclusão."

    return render_template(
        "aprovacoes.html",
        equipes=dados.get("equipes", {}),
        sucesso=sucesso,
        erro=erro
    )


# =========================================================
# COMPETIÇÕES
# =========================================================
@app.route("/competicoes")
def competicoes():
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()
    return render_template("competicoes.html", competicoes=dados.get("competicoes", {}))


@app.route("/nova-competicao", methods=["GET", "POST"])
def nova_competicao():
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()
    erro = None
    sucesso = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cidade = request.form.get("cidade", "").strip()
        ginasio = request.form.get("ginasio", "").strip()
        categoria = request.form.get("categoria", "").strip()
        sexo = request.form.get("sexo", "").strip()

        if not nome:
            erro = "O nome da competição é obrigatório."
        else:
            if "competicoes" not in dados:
                dados["competicoes"] = {}

            if nome in dados["competicoes"]:
                erro = "Já existe uma competição com esse nome."
            else:
                dados["competicoes"][nome] = {
                    "dados": {
                        "nome": nome,
                        "cidade": cidade,
                        "ginasio": ginasio,
                        "categoria": categoria,
                        "sexo": sexo
                    },
                    "equipes": {},
                    "partidas": {}
                }
                salvar_dados(dados)
                sucesso = "Competição criada com sucesso."

    return render_template("nova_competicao.html", erro=erro, sucesso=sucesso)


# =========================================================
# PRAZOS
# =========================================================
@app.route("/prazos", methods=["GET", "POST"])
def prazos():
    if not exige_login():
        return redirect(url_for("login"))

    dados = obter_dados()

    if "configuracoes" not in dados:
        dados["configuracoes"] = {
            "prazo_cadastro_atletas": "",
            "prazo_edicao_atletas": ""
        }

    sucesso = None
    erro = None

    if request.method == "POST":
        dados["configuracoes"]["prazo_cadastro_atletas"] = request.form.get("prazo_cadastro_atletas", "").strip()
        dados["configuracoes"]["prazo_edicao_atletas"] = request.form.get("prazo_edicao_atletas", "").strip()
        salvar_dados(dados)
        sucesso = "Prazos salvos com sucesso."

    return render_template(
        "prazos.html",
        configuracoes=dados["configuracoes"],
        sucesso=sucesso,
        erro=erro
    )


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
            atleta for atleta in equipe.get("atletas", [])
            if atleta.get("status") == "aprovado"
        ]

        if atletas_aprovados:
            equipes_filtradas[nome_eq] = {
                "nome": nome_eq,
                "atletas": atletas_aprovados
            }

    return render_template("listagem_oficial.html", equipes=equipes_filtradas)


# =========================================================
# PÁGINAS SIMPLES
# =========================================================
@app.route("/tabela")
def tabela():
    if not exige_login():
        return redirect(url_for("login"))
    return render_template("pagina_simples.html", titulo="Tabela")


@app.route("/pre-jogo")
def pre_jogo():
    if not exige_login():
        return redirect(url_for("login"))
    return render_template("pagina_simples.html", titulo="Pré-jogo")


@app.route("/jogo")
def jogo():
    if not exige_login():
        return redirect(url_for("login"))
    return render_template("pagina_simples.html", titulo="Jogo")


@app.route("/pagina-simples")
def pagina_simples():
    if not exige_login():
        return redirect(url_for("login"))
    return render_template("pagina_simples.html", titulo="Página Simples")


# =========================================================
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    inicializar_banco()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)