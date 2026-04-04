def nome_equipe_por_chave(dados, chave_equipe):
    if not chave_equipe:
        return None

    equipe = dados.get("equipes", {}).get(chave_equipe)
    if equipe:
        return equipe.get("nome", chave_equipe)

    return chave_equipe


def garantir_estrutura_dados(dados):
    if not dados or not isinstance(dados, dict):
        dados = {}

    if "usuarios" not in dados or not isinstance(dados["usuarios"], dict):
        dados["usuarios"] = {}

    if "equipes" not in dados or not isinstance(dados["equipes"], dict):
        dados["equipes"] = {}

    if "competicoes" not in dados or not isinstance(dados["competicoes"], dict):
        dados["competicoes"] = {}

    if "configuracoes" not in dados or not isinstance(dados["configuracoes"], dict):
        dados["configuracoes"] = {
            "prazo_cadastro_atletas": "",
            "prazo_edicao_atletas": ""
        }

    for login, usuario in dados["usuarios"].items():
        if "nome" not in usuario:
            usuario["nome"] = login
        if "ativo" not in usuario:
            usuario["ativo"] = True
        if "equipe" not in usuario:
            usuario["equipe"] = None
        if "competicao_vinculada" not in usuario:
            usuario["competicao_vinculada"] = ""
        if "acesso_ate" not in usuario:
            usuario["acesso_ate"] = ""

    return dados