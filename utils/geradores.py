import random
import string


def gerar_login_equipe(nome, usuarios_existentes):
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

    while login in usuarios_existentes:
        login = f"{base}_{contador}"
        contador += 1

    return login


def gerar_senha():
    caracteres = string.ascii_letters + string.digits
    return "".join(random.choice(caracteres) for _ in range(6))


def gerar_senha_automatica():
    return gerar_senha()


def gerar_login_organizador(nome_competicao, usuarios_existentes):
    base = nome_competicao.strip().lower()
    caracteres_invalidos = ".,;:/\\|!?@#$%¨&*()[]{}=+´`~^'\""
    for c in caracteres_invalidos:
        base = base.replace(c, "")
    base = base.replace("-", " ")
    base = "_".join(base.split())

    if not base:
        base = "competicao"

    login = f"org_{base}"
    contador = 1

    while login in usuarios_existentes:
        login = f"org_{base}_{contador}"
        contador += 1

    return login


def gerar_chave_equipe(nome_equipe, competicao_vinculada, equipes_existentes):
    base_nome = nome_equipe.strip().lower()
    caracteres_invalidos = ".,;:/\\|!?@#$%¨&*()[]{}=+´`~^'\""
    for c in caracteres_invalidos:
        base_nome = base_nome.replace(c, "")
    base_nome = base_nome.replace("-", " ")
    base_nome = "_".join(base_nome.split())

    base_comp = (competicao_vinculada or "sem_competicao").strip().lower()
    for c in caracteres_invalidos:
        base_comp = base_comp.replace(c, "")
    base_comp = base_comp.replace("-", " ")
    base_comp = "_".join(base_comp.split())

    chave_base = f"{base_nome}__{base_comp}"
    chave = chave_base
    contador = 1

    while chave in equipes_existentes:
        chave = f"{chave_base}_{contador}"
        contador += 1

    return chave


# =========================================================
# CPF
# =========================================================
def limpar_cpf(cpf):
    if not cpf:
        return ""
    return "".join(filter(str.isdigit, cpf))


def cpf_valido(cpf):
    cpf = limpar_cpf(cpf)

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    # Primeiro dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma * 10 % 11) % 10

    # Segundo dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma * 10 % 11) % 10

    return cpf[-2:] == f"{dig1}{dig2}"