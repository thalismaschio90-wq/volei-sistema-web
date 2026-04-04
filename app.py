from flask import Flask, render_template, request, redirect, session, url_for
import os

from utils.auth_utils import (
    usuario_logado,
    perfil_atual,
    equipe_atual,
    nome_usuario_atual,
    exige_login,
    exige_perfil,
)

from utils.geradores import (
    gerar_login_equipe,
    gerar_senha_automatica,
    limpar_cpf,
    cpf_valido,
)

from banco import obter_dados, salvar_dados

app = Flask(__name__)
app.secret_key = "voleibol123"


# =========================================================
# AUXILIAR
# =========================================================
def garantir_estrutura(dados):
    if not isinstance(dados, dict):
        dados = {}

    dados.setdefault("usuarios", {})
    dados.setdefault("equipes", {})
    dados.setdefault("competicoes", {})
    dados.setdefault("configuracoes", {
        "prazo_cadastro_atletas": "",
        "prazo_edicao_atletas": ""
    })

    for login, usuario in dados["usuarios"].items():
        if not isinstance(usuario, dict):
            dados["usuarios"][login] = {}
            usuario = dados["usuarios"][login]

        usuario.setdefault("nome", login)
        usuario.setdefault("senha", "")
        usuario.setdefault("perfil", "")
        usuario.setdefault("ativo", True)
        usuario.setdefault("equipe", None)
        usuario.setdefault("competicao_vinculada", "")
        usuario.setdefault("acesso_ate", "")

    for nome_eq, equipe in dados["equipes"].items():
        if not isinstance(equipe, dict):
            dados["equipes"][nome_eq] = {}
            equipe = dados["equipes"][nome_eq]

        equipe.setdefault("nome", nome_eq)
        equipe.setdefault("login", "")
        equipe.setdefault("senha", "")
        equipe.setdefault("atletas", [])
        equipe.setdefault("competicao", "")

    for nome_comp, comp in dados["competicoes"].items():
        if not isinstance(comp, dict):
            dados["competicoes"][nome_comp] = {}
            comp = dados["competicoes"][nome_comp]

        comp.setdefault("nome", nome_comp)
        comp.setdefault("data", "")
        comp.setdefault("status", "pendente")
        comp.setdefault("organizador_login", "")
        comp.setdefault("organizador", {"login": "", "senha": ""})
        comp.setdefault("dados", {
            "cidade": "",
            "ginasio": "",
            "categoria": "",
            "sexo": "",
            "divisao": ""
        })

    return dados


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

        dados = garantir_estrutura(obter_dados())
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
@app.route("/painel-superadmin")
def painel_superadmin():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())
    usuarios = dados.get("usuarios", {})
    equipes = dados.get("equipes", {})

    total_aprovados = 0
    for eq in equipes.values():
        for atleta in eq.get("atletas", []):
            if atleta.get("status") == "aprovado":
                total_aprovados += 1

    resumo = {
        "total_usuarios": len(usuarios),
        "total_organizadores": sum(1 for u in usuarios.values() if u.get("perfil") == "organizador"),
        "total_mesarios": sum(1 for u in usuarios.values() if u.get("perfil") == "mesario"),
        "total_equipes": len(equipes),
        "total_atletas": sum(len(eq.get("atletas", [])) for eq in equipes.values()),
        "total_aprovados": total_aprovados,
    }

    return render_template("painel_superadmin.html", resumo=resumo)


@app.route("/painel-organizador")
def painel_organizador():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["organizador"]):
        return redirect(url_for("index"))

    return render_template("painel_organizador.html")


@app.route("/painel-mesario")
def painel_mesario():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["mesario"]):
        return redirect(url_for("index"))

    return render_template("painel_mesario.html")


# =========================================================
# MINHA CONTA
# =========================================================
@app.route("/minha-conta", methods=["GET", "POST"])
def minha_conta():
    if not exige_login():
        return redirect(url_for("login"))

    dados = garantir_estrutura(obter_dados())
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
            senha_atual_login = request.form.get("senha_atual_login", "").strip()

            if not novo_login:
                erro_login = "O novo login é obrigatório."
            elif senha_atual_login != usuario.get("senha"):
                erro_login = "Senha atual incorreta."
            elif novo_login == login_atual:
                erro_login = "O novo login não pode ser igual ao atual."
            elif novo_login in dados["usuarios"]:
                erro_login = "Esse login já existe."
            else:
                dados["usuarios"][novo_login] = dados["usuarios"].pop(login_atual)

                equipe_nome = dados["usuarios"][novo_login].get("equipe")
                if equipe_nome and equipe_nome in dados["equipes"]:
                    dados["equipes"][equipe_nome]["login"] = novo_login

                for _, comp in dados.get("competicoes", {}).items():
                    if comp.get("organizador_login") == login_atual:
                        comp["organizador_login"] = novo_login
                    if comp.get("organizador", {}).get("login") == login_atual:
                        comp["organizador"]["login"] = novo_login

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

                equipe_nome = dados["usuarios"][login_atual].get("equipe")
                if equipe_nome and equipe_nome in dados["equipes"]:
                    dados["equipes"][equipe_nome]["senha"] = nova_senha

                for _, comp in dados.get("competicoes", {}).items():
                    if comp.get("organizador_login") == login_atual:
                        comp["organizador"]["senha"] = nova_senha

                salvar_dados(dados)
                sucesso_senha = "Senha alterada com sucesso."

    return render_template(
        "minha_conta.html",
        login_atual=login_atual,
        usuario=usuario,
        erro_login=erro_login,
        sucesso_login=sucesso_login,
        erro_senha=erro_senha,
        sucesso_senha=sucesso_senha,
    )


# =========================================================
# COMPETIÇÕES
# =========================================================
@app.route("/competicoes")
def competicoes():
    if not exige_login():
        return redirect(url_for("login"))

    dados = garantir_estrutura(obter_dados())
    competicoes_dict = dados.get("competicoes", {})

    if perfil_atual() == "superadmin":
        lista = {}
        for nome, comp in competicoes_dict.items():
            lista[nome] = {
                "nome": nome,
                "data": comp.get("data", "-"),
                "status": comp.get("status", "pendente"),
                "organizador_login": comp.get("organizador_login", "-"),
            }
    elif perfil_atual() == "organizador":
        usuario = dados["usuarios"].get(nome_usuario_atual(), {})
        nome_comp = usuario.get("competicao_vinculada", "")
        lista = {}
        if nome_comp in competicoes_dict:
            comp = competicoes_dict[nome_comp]
            lista[nome_comp] = {
                "nome": nome_comp,
                "data": comp.get("data", "-"),
                "status": comp.get("status", "pendente"),
                "organizador_login": comp.get("organizador_login", "-"),
            }
    else:
        return redirect(url_for("index"))

    return render_template("competicoes.html", competicoes=lista)


@app.route("/competicoes/nova", methods=["GET", "POST"])
def nova_competicao():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())

    erro = None
    sucesso = None
    dados_gerados = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        data = request.form.get("data", "").strip()

        if not nome or not data:
            erro = "Preencha todos os campos."
        elif nome in dados["competicoes"]:
            erro = "Já existe uma competição com esse nome."
        else:
            login_base = gerar_login_equipe(nome, dados["usuarios"])
            login_org = f"org_{login_base}"
            contador = 1
            while login_org in dados["usuarios"]:
                login_org = f"org_{login_base}_{contador}"
                contador += 1

            senha_org = gerar_senha_automatica()

            dados["usuarios"][login_org] = {
                "nome": f"Organizador {nome}",
                "senha": senha_org,
                "perfil": "organizador",
                "ativo": True,
                "equipe": None,
                "competicao_vinculada": nome,
                "acesso_ate": ""
            }

            dados["competicoes"][nome] = {
                "nome": nome,
                "data": data,
                "status": "pendente",
                "organizador_login": login_org,
                "organizador": {
                    "login": login_org,
                    "senha": senha_org
                },
                "dados": {
                    "cidade": "",
                    "ginasio": "",
                    "categoria": "",
                    "sexo": "",
                    "divisao": ""
                }
            }

            salvar_dados(dados)

            sucesso = "Competição criada com sucesso."
            dados_gerados = {
                "nome": nome,
                "data": data,
                "login": login_org,
                "senha": senha_org
            }

    return render_template("nova_competicao.html", erro=erro, sucesso=sucesso, dados_gerados=dados_gerados)


@app.route("/competicoes/editar/<nome>", methods=["GET", "POST"])
def editar_competicao(nome):
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["organizador"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())
    usuario = dados["usuarios"].get(nome_usuario_atual(), {})

    if usuario.get("competicao_vinculada") != nome:
        return redirect(url_for("index"))

    competicao = dados["competicoes"].get(nome)
    if not competicao:
        return redirect(url_for("competicoes"))

    erro = None
    sucesso = None

    if request.method == "POST":
        competicao["dados"]["cidade"] = request.form.get("cidade", "").strip()
        competicao["dados"]["ginasio"] = request.form.get("ginasio", "").strip()
        competicao["dados"]["categoria"] = request.form.get("categoria", "").strip()
        competicao["dados"]["sexo"] = request.form.get("sexo", "").strip()
        competicao["dados"]["divisao"] = request.form.get("divisao", "").strip()

        if competicao.get("status") == "pendente":
            competicao["status"] = "em_configuracao"

        salvar_dados(dados)
        sucesso = "Dados salvos com sucesso."

    return render_template(
        "editar_competicao.html",
        nome=nome,
        competicao=competicao,
        erro=erro,
        sucesso=sucesso
    )


@app.route("/competicoes/gerenciar/<nome>", methods=["GET", "POST"])
def gerenciar_competicao_superadmin(nome):
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())
    comp = dados.get("competicoes", {}).get(nome)

    if not comp:
        return redirect(url_for("competicoes"))

    organizador_login = comp.get("organizador_login")
    organizador = dados["usuarios"].get(organizador_login, {})

    sucesso = None
    erro = None

    if request.method == "POST":
        acao = request.form.get("acao")

        if acao == "redefinir_senha":
            nova = gerar_senha_automatica()
            if organizador_login in dados["usuarios"]:
                dados["usuarios"][organizador_login]["senha"] = nova
            comp.setdefault("organizador", {})
            comp["organizador"]["senha"] = nova
            salvar_dados(dados)
            sucesso = f"Nova senha: {nova}"

        elif acao == "excluir_competicao":
            if organizador_login in dados["usuarios"]:
                del dados["usuarios"][organizador_login]

            equipes_remover = []
            for nome_eq, equipe in dados.get("equipes", {}).items():
                if equipe.get("competicao") == nome:
                    equipes_remover.append(nome_eq)

            for nome_eq in equipes_remover:
                login_eq = dados["equipes"][nome_eq].get("login")
                if login_eq in dados["usuarios"]:
                    del dados["usuarios"][login_eq]
                del dados["equipes"][nome_eq]

            usuarios_remover = []
            for login, usuario in dados.get("usuarios", {}).items():
                if usuario.get("competicao_vinculada") == nome:
                    usuarios_remover.append(login)

            for login in usuarios_remover:
                if login in dados["usuarios"]:
                    del dados["usuarios"][login]

            dados["competicoes"].pop(nome, None)
            salvar_dados(dados)
            return redirect(url_for("competicoes"))

    return render_template(
        "gerenciar_competicao_superadmin.html",
        nome=nome,
        competicao=comp,
        organizador_login=organizador_login,
        organizador=organizador,
        sucesso=sucesso,
        erro=erro
    )


# =========================================================
# USUÁRIOS
# =========================================================
@app.route("/usuarios")
def usuarios():
    if not exige_login():
        return redirect(url_for("login"))

    dados = garantir_estrutura(obter_dados())

    if perfil_atual() == "superadmin":
        lista = dados["usuarios"]
    elif perfil_atual() == "organizador":
        comp = dados["usuarios"].get(nome_usuario_atual(), {}).get("competicao_vinculada", "")
        lista = {
            login: usuario
            for login, usuario in dados["usuarios"].items()
            if usuario.get("competicao_vinculada", "") == comp
        }
    else:
        return redirect(url_for("index"))

    return render_template("usuarios.html", usuarios=lista)


@app.route("/usuarios/novo", methods=["GET", "POST"])
def novo_usuario():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())
    erro = None
    sucesso = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        login = request.form.get("login", "").strip()
        senha = request.form.get("senha", "").strip()
        perfil = request.form.get("perfil", "").strip()
        ativo = request.form.get("ativo") == "on"
        acesso_ate = request.form.get("acesso_ate", "").strip()

        if not nome or not login or not senha or not perfil:
            erro = "Preencha todos os campos obrigatórios."
        elif login in dados["usuarios"]:
            erro = "Já existe um usuário com esse login."
        else:
            comp_vinculada = ""
            if perfil_atual() == "organizador":
                comp_vinculada = dados["usuarios"].get(nome_usuario_atual(), {}).get("competicao_vinculada", "")
                if perfil not in ["mesario", "equipe"]:
                    erro = "Organizador só pode criar mesário e equipe."

            if not erro:
                dados["usuarios"][login] = {
                    "nome": nome,
                    "senha": senha,
                    "perfil": perfil,
                    "ativo": ativo,
                    "equipe": None,
                    "acesso_ate": acesso_ate if perfil == "organizador" else "",
                    "competicao_vinculada": comp_vinculada
                }
                salvar_dados(dados)
                sucesso = "Usuário criado com sucesso."

    return render_template("novo_usuario.html", erro=erro, sucesso=sucesso)


@app.route("/usuarios/editar/<login_usuario>", methods=["GET", "POST"])
def editar_usuario(login_usuario):
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())

    if login_usuario not in dados["usuarios"]:
        return redirect(url_for("usuarios"))

    usuario = dados["usuarios"][login_usuario]
    erro = None
    sucesso = None

    if perfil_atual() == "organizador":
        comp = dados["usuarios"].get(nome_usuario_atual(), {}).get("competicao_vinculada", "")
        if usuario.get("competicao_vinculada", "") != comp:
            return redirect(url_for("usuarios"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        senha = request.form.get("senha", "").strip()
        perfil = request.form.get("perfil", "").strip()
        ativo = request.form.get("ativo") == "on"
        acesso_ate = request.form.get("acesso_ate", "").strip()

        if not nome or not perfil:
            erro = "Nome e perfil são obrigatórios."
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

    dados = garantir_estrutura(obter_dados())

    if perfil_atual() == "superadmin":
        lista = dados["equipes"]
    elif perfil_atual() == "organizador":
        comp = dados["usuarios"].get(nome_usuario_atual(), {}).get("competicao_vinculada", "")
        lista = {
            nome: equipe
            for nome, equipe in dados["equipes"].items()
            if equipe.get("competicao", "") == comp
        }
    else:
        return redirect(url_for("index"))

    return render_template("equipes.html", equipes=lista)


@app.route("/equipes/nova", methods=["GET", "POST"])
def nova_equipe():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())
    erro = None
    sucesso = None
    dados_gerados = None

    if request.method == "POST":
        nome_equipe = request.form.get("nome_equipe", "").strip()

        if not nome_equipe:
            erro = "O nome da equipe é obrigatório."
        else:
            comp_vinculada = ""
            if perfil_atual() == "organizador":
                comp_vinculada = dados["usuarios"].get(nome_usuario_atual(), {}).get("competicao_vinculada", "")

            equipe_duplicada = False
            for nome_existente, equipe_existente in dados["equipes"].items():
                mesmo_nome = nome_existente.strip().lower() == nome_equipe.strip().lower()
                if not mesmo_nome:
                    continue

                if perfil_atual() == "superadmin":
                    equipe_duplicada = True
                    break

                if equipe_existente.get("competicao", "") == comp_vinculada:
                    equipe_duplicada = True
                    break

            if equipe_duplicada:
                erro = "Já existe uma equipe com esse nome nesta competição."
            else:
                login_gerado = gerar_login_equipe(nome_equipe, dados["usuarios"])
                senha_gerada = gerar_senha_automatica()

                dados["equipes"][nome_equipe] = {
                    "nome": nome_equipe,
                    "login": login_gerado,
                    "senha": senha_gerada,
                    "atletas": [],
                    "competicao": comp_vinculada
                }

                dados["usuarios"][login_gerado] = {
                    "nome": nome_equipe,
                    "senha": senha_gerada,
                    "perfil": "equipe",
                    "ativo": True,
                    "equipe": nome_equipe,
                    "competicao_vinculada": comp_vinculada
                }

                salvar_dados(dados)

                sucesso = "Equipe criada com sucesso."
                dados_gerados = {
                    "nome_equipe": nome_equipe,
                    "login": login_gerado,
                    "senha": senha_gerada,
                }

    return render_template(
        "nova_equipe.html",
        erro=erro,
        sucesso=sucesso,
        dados_gerados=dados_gerados,
    )


# =========================================================
# APROVAÇÕES
# =========================================================
@app.route("/aprovacoes", methods=["GET", "POST"])
def aprovacoes():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())
    sucesso = None
    erro = None

    if request.method == "POST":
        acao = request.form.get("acao", "").strip()
        equipe_nome = request.form.get("equipe", "").strip()
        cpf = request.form.get("cpf", "").strip()

        if equipe_nome in dados["equipes"]:
            atletas = dados["equipes"][equipe_nome].get("atletas", [])

            if acao in ["aprovar", "rejeitar"]:
                for atleta in atletas:
                    if atleta.get("cpf") == cpf:
                        atleta["status"] = "aprovado" if acao == "aprovar" else "rejeitado"
                        sucesso = "Atleta atualizado com sucesso."
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
                    erro = "Atleta não encontrado."

    if perfil_atual() == "organizador":
        comp = dados["usuarios"].get(nome_usuario_atual(), {}).get("competicao_vinculada", "")
        equipes_exibir = {
            nome: equipe
            for nome, equipe in dados["equipes"].items()
            if equipe.get("competicao", "") == comp
        }
    else:
        equipes_exibir = dados["equipes"]

    return render_template("aprovacoes.html", equipes=equipes_exibir, sucesso=sucesso, erro=erro)


# =========================================================
# LISTAGEM OFICIAL
# =========================================================
@app.route("/listagem-oficial")
def listagem_oficial():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())

    if perfil_atual() == "organizador":
        comp = dados["usuarios"].get(nome_usuario_atual(), {}).get("competicao_vinculada", "")
        equipes_base = {
            nome: equipe
            for nome, equipe in dados["equipes"].items()
            if equipe.get("competicao", "") == comp
        }
    else:
        equipes_base = dados["equipes"]

    equipes_filtradas = {}
    for nome_eq, equipe in equipes_base.items():
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
# PRAZOS
# =========================================================
@app.route("/prazos", methods=["GET", "POST"])
def prazos():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())
    sucesso = None
    erro = None

    if request.method == "POST":
        dados["configuracoes"]["prazo_cadastro_atletas"] = request.form.get("prazo_cadastro_atletas", "")
        dados["configuracoes"]["prazo_edicao_atletas"] = request.form.get("prazo_edicao_atletas", "")
        salvar_dados(dados)
        sucesso = "Prazos salvos com sucesso."

    return render_template("prazos.html", configuracoes=dados["configuracoes"], sucesso=sucesso, erro=erro)


# =========================================================
# TABELA / PRÉ-JOGO / JOGO
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


# =========================================================
# PORTAL DA EQUIPE
# =========================================================
@app.route("/meu-time", methods=["GET", "POST"])
def meu_time():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["equipe"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura(obter_dados())
    nome_eq = equipe_atual()

    if not nome_eq or nome_eq not in dados.get("equipes", {}):
        return redirect(url_for("logout"))

    equipe = dados["equipes"][nome_eq]
    erro = None
    sucesso = None

    prazo_cadastro = dados.get("configuracoes", {}).get("prazo_cadastro_atletas", "")
    prazo_edicao = dados.get("configuracoes", {}).get("prazo_edicao_atletas", "")
    cadastro_bloqueado = False
    edicao_bloqueada = False

    if request.method == "POST":
        acao = request.form.get("acao", "").strip()

        if acao == "excluir":
            cpf = request.form.get("cpf", "").strip()
            indice_remover = None

            for i, atleta in enumerate(equipe["atletas"]):
                if atleta.get("cpf") == cpf:
                    indice_remover = i
                    break

            if indice_remover is not None:
                equipe["atletas"].pop(indice_remover)
                salvar_dados(dados)
                sucesso = "Atleta excluído com sucesso."
            else:
                erro = "Atleta não encontrado."

        else:
            nome = request.form.get("nome", "").strip()
            numero = request.form.get("numero", "").strip()
            cpf = limpar_cpf(request.form.get("cpf", "").strip())
            data_nascimento = request.form.get("data_nascimento", "").strip()

            if not nome or not cpf or not data_nascimento:
                erro = "Nome, CPF e data de nascimento são obrigatórios."
            elif not cpf_valido(cpf):
                erro = "CPF inválido."
            else:
                for atleta in equipe["atletas"]:
                    if limpar_cpf(atleta.get("cpf", "")) == cpf:
                        erro = "Este CPF já está cadastrado nesta equipe."
                        break

                if not erro:
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
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True)