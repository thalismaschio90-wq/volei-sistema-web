from flask import session


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