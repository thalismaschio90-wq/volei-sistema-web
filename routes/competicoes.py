from flask import Blueprint, render_template, request, redirect, url_for

from banco import obter_dados, salvar_dados
from utils.auth_utils import exige_login, exige_perfil, perfil_atual, nome_usuario_atual
from utils.estrutura import garantir_estrutura_dados
from utils.geradores import gerar_login_organizador, gerar_senha


competicoes_bp = Blueprint("competicoes_bp", __name__)


@competicoes_bp.route("/competicoes")
def competicoes():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura_dados(obter_dados())
    competicoes_dict = dados.get("competicoes", {})

    if perfil_atual() == "superadmin":
        competicoes_exibidas = competicoes_dict
    else:
        usuario_atual = dados["usuarios"].get(nome_usuario_atual(), {})
        competicao_vinculada = usuario_atual.get("competicao_vinculada", "")
        competicoes_exibidas = {}

        if competicao_vinculada and competicao_vinculada in competicoes_dict:
            competicoes_exibidas[competicao_vinculada] = competicoes_dict[competicao_vinculada]

    return render_template("competicoes.html", competicoes=competicoes_exibidas)


@competicoes_bp.route("/competicoes/nova", methods=["GET", "POST"])
def nova_competicao():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura_dados(obter_dados())
    erro = None
    sucesso = None
    dados_gerados = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        data = request.form.get("data", "").strip()

        if not nome or not data:
            erro = "O nome e a data da competição são obrigatórios."
        elif nome in dados["competicoes"]:
            erro = "Já existe uma competição com esse nome."
        else:
            login_organizador = gerar_login_organizador(nome, dados["usuarios"])
            senha_organizador = gerar_senha()

            dados["usuarios"][login_organizador] = {
                "nome": f"Organizador - {nome}",
                "senha": senha_organizador,
                "perfil": "organizador",
                "ativo": True,
                "equipe": None,
                "acesso_ate": "",
                "competicao_vinculada": nome
            }

            dados["competicoes"][nome] = {
                "nome": nome,
                "data": data,
                "status": "pendente",
                "organizador_login": login_organizador,
                "organizador": {
                    "login": login_organizador,
                    "senha": senha_organizador
                },
                "dados": {
                    "cidade": "",
                    "ginasio": "",
                    "categoria": "",
                    "sexo": "",
                    "divisao": ""
                },
                "regras": {},
                "arbitragem": [],
                "equipes": {},
                "mesarios": {}
            }

            salvar_dados(dados)

            sucesso = "Competição criada com sucesso."
            dados_gerados = {
                "nome": nome,
                "data": data,
                "login": login_organizador,
                "senha": senha_organizador
            }

    return render_template(
        "nova_competicao.html",
        erro=erro,
        sucesso=sucesso,
        dados_gerados=dados_gerados
    )


@competicoes_bp.route("/competicoes/editar/<nome>", methods=["GET", "POST"])
def editar_competicao(nome):
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["organizador"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura_dados(obter_dados())

    usuario = dados["usuarios"].get(nome_usuario_atual(), {})
    if usuario.get("competicao_vinculada") != nome:
        return redirect(url_for("index"))

    competicao = dados["competicoes"].get(nome)
    if not competicao:
        return redirect(url_for("competicoes_bp.competicoes"))

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
        competicao=competicao,
        nome=nome,
        erro=erro,
        sucesso=sucesso
    )


@competicoes_bp.route("/competicoes/gerenciar/<nome>", methods=["GET", "POST"])
def gerenciar_competicao_superadmin(nome):
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    dados = garantir_estrutura_dados(obter_dados())
    competicao = dados.get("competicoes", {}).get(nome)

    if not competicao:
        return redirect(url_for("competicoes_bp.competicoes"))

    erro = None
    sucesso = None
    organizador_login = competicao.get("organizador_login", "")
    organizador = dados.get("usuarios", {}).get(organizador_login, {})

    if request.method == "POST":
        acao = request.form.get("acao", "").strip()

        if acao == "redefinir_senha":
            nova_senha = gerar_senha()

            if organizador_login in dados["usuarios"]:
                dados["usuarios"][organizador_login]["senha"] = nova_senha

            competicao.setdefault("organizador", {})
            competicao["organizador"]["login"] = organizador_login
            competicao["organizador"]["senha"] = nova_senha

            salvar_dados(dados)
            sucesso = f"Senha do organizador redefinida com sucesso. Nova senha: {nova_senha}"
            organizador = dados.get("usuarios", {}).get(organizador_login, {})

        elif acao == "excluir_competicao":
            usuarios_para_excluir = []
            for login, usuario in dados.get("usuarios", {}).items():
                if usuario.get("competicao_vinculada", "") == nome:
                    usuarios_para_excluir.append(login)

            equipes_para_excluir = []
            for chave_equipe, equipe in dados.get("equipes", {}).items():
                if equipe.get("competicao_vinculada", "") == nome:
                    equipes_para_excluir.append(chave_equipe)

            for login in usuarios_para_excluir:
                if login in dados["usuarios"]:
                    del dados["usuarios"][login]

            for chave_equipe in equipes_para_excluir:
                if chave_equipe in dados["equipes"]:
                    del dados["equipes"][chave_equipe]

            if nome in dados.get("competicoes", {}):
                del dados["competicoes"][nome]

            salvar_dados(dados)
            return redirect(url_for("competicoes_bp.competicoes"))

    return render_template(
        "gerenciar_competicao_superadmin.html",
        competicao=competicao,
        nome=nome,
        organizador_login=organizador_login,
        organizador=organizador,
        erro=erro,
        sucesso=sucesso
    )