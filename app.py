from flask import Flask, render_template, request, redirect, session, url_for
import os
import random
import string
from datetime import timedelta
from banco import criar_tabelas, importar_json_se_existir, conectar

app = Flask(__name__)
app.secret_key = "voleibol123"
app.permanent_session_lifetime = timedelta(minutes=30)

criar_tabelas()
importar_json_se_existir("dados.json")


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
    return usuario_logado()


def exige_perfil(perfis_permitidos):
    return perfil_atual() in perfis_permitidos


@app.before_request
def renovar_sessao():
    if usuario_logado():
        session.permanent = True
        session.modified = True


def limpar_cpf(cpf):
    return "".join(ch for ch in str(cpf) if ch.isdigit())


def cpf_valido(cpf):
    cpf = limpar_cpf(cpf)

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    soma_1 = 0
    for i in range(9):
        soma_1 += int(cpf[i]) * (10 - i)
    resto_1 = (soma_1 * 10) % 11
    if resto_1 == 10:
        resto_1 = 0
    if resto_1 != int(cpf[9]):
        return False

    soma_2 = 0
    for i in range(10):
        soma_2 += int(cpf[i]) * (11 - i)
    resto_2 = (soma_2 * 10) % 11
    if resto_2 == 10:
        resto_2 = 0
    if resto_2 != int(cpf[10]):
        return False

    return True


def gerar_senha_automatica(tamanho=7):
    caracteres = string.ascii_letters + string.digits
    return "".join(random.choice(caracteres) for _ in range(tamanho))


def listar_logins_existentes():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT login FROM usuarios")
    logins = [row["login"] for row in cur.fetchall()]
    conn.close()
    return logins


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


def listar_usuarios_dict():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT login, nome, senha, perfil, ativo, equipe
        FROM usuarios
        ORDER BY login
    """)
    rows = cur.fetchall()
    conn.close()

    usuarios = {}
    for row in rows:
        usuarios[row["login"]] = {
            "nome": row["nome"],
            "senha": row["senha"],
            "perfil": row["perfil"],
            "ativo": bool(row["ativo"]),
            "equipe": row["equipe"]
        }
    return usuarios


def obter_usuario(login):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT login, nome, senha, perfil, ativo, equipe
        FROM usuarios
        WHERE login = ?
    """, (login,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "login": row["login"],
        "nome": row["nome"],
        "senha": row["senha"],
        "perfil": row["perfil"],
        "ativo": bool(row["ativo"]),
        "equipe": row["equipe"]
    }


def listar_equipes_dict():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT nome, login, senha
        FROM equipes
        ORDER BY nome
    """)
    equipes_rows = cur.fetchall()

    equipes = {}
    for row in equipes_rows:
        equipes[row["nome"]] = {
            "nome": row["nome"],
            "login": row["login"],
            "senha": row["senha"],
            "atletas": []
        }

    cur.execute("""
        SELECT id, equipe_nome, nome, numero, cpf, data_nascimento, status
        FROM atletas
        ORDER BY equipe_nome, nome
    """)
    atletas_rows = cur.fetchall()

    for row in atletas_rows:
        equipe_nome = row["equipe_nome"]
        if equipe_nome not in equipes:
            equipes[equipe_nome] = {
                "nome": equipe_nome,
                "login": "",
                "senha": "",
                "atletas": []
            }

        equipes[equipe_nome]["atletas"].append({
            "id": row["id"],
            "nome": row["nome"],
            "numero": row["numero"],
            "cpf": row["cpf"],
            "data_nascimento": row["data_nascimento"],
            "status": row["status"]
        })

    conn.close()
    return equipes


def obter_equipe(nome_equipe):
    equipes = listar_equipes_dict()
    return equipes.get(nome_equipe)


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

        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT login, nome, senha, perfil, ativo, equipe
            FROM usuarios
            WHERE login = ?
        """, (usuario,))
        row = cur.fetchone()
        conn.close()

        if row:
            if not bool(row["ativo"]):
                erro = "Usuário inativo."
            elif row["senha"] == senha:
                session["usuario"] = row["login"]
                session["perfil"] = row["perfil"]
                session["equipe"] = row["equipe"]
                session.permanent = True
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

    login_atual = nome_usuario_atual()
    usuario = obter_usuario(login_atual)

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
            elif obter_usuario(novo_login):
                erro_login = "Esse login já existe."
            else:
                conn = conectar()
                cur = conn.cursor()

                cur.execute("""
                    UPDATE usuarios
                    SET login = ?
                    WHERE login = ?
                """, (novo_login, login_atual))

                if usuario.get("equipe"):
                    cur.execute("""
                        UPDATE equipes
                        SET login = ?
                        WHERE nome = ?
                    """, (novo_login, usuario["equipe"]))

                conn.commit()
                conn.close()

                session["usuario"] = novo_login
                login_atual = novo_login
                usuario = obter_usuario(novo_login)

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
                conn = conectar()
                cur = conn.cursor()

                cur.execute("""
                    UPDATE usuarios
                    SET senha = ?
                    WHERE login = ?
                """, (nova_senha, login_atual))

                if usuario.get("equipe"):
                    cur.execute("""
                        UPDATE equipes
                        SET senha = ?
                        WHERE nome = ?
                    """, (nova_senha, usuario["equipe"]))

                conn.commit()
                conn.close()

                usuario = obter_usuario(login_atual)
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

    return render_template("usuarios.html", usuarios=listar_usuarios_dict())


@app.route("/usuarios/novo", methods=["GET", "POST"])
def novo_usuario():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    erro = None
    sucesso = None

    if request.method == "POST":
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
        elif obter_usuario(login):
            erro = "Já existe um usuário com esse login."
        else:
            conn = conectar()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO usuarios (login, nome, senha, perfil, ativo, equipe)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (login, nome, senha, perfil, 1 if ativo else 0, None))
            conn.commit()
            conn.close()
            sucesso = "Usuário criado com sucesso."

    return render_template("novo_usuario.html", erro=erro, sucesso=sucesso)


@app.route("/usuarios/editar/<login_usuario>", methods=["GET", "POST"])
def editar_usuario(login_usuario):
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin"]):
        return redirect(url_for("index"))

    usuario = obter_usuario(login_usuario)

    if not usuario:
        return redirect(url_for("usuarios"))

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
            conn = conectar()
            cur = conn.cursor()

            cur.execute("""
                UPDATE usuarios
                SET nome = ?, perfil = ?, ativo = ?
                WHERE login = ?
            """, (nome, perfil, 1 if ativo else 0, login_usuario))

            if senha:
                cur.execute("""
                    UPDATE usuarios
                    SET senha = ?
                    WHERE login = ?
                """, (senha, login_usuario))

                if usuario.get("equipe"):
                    cur.execute("""
                        UPDATE equipes
                        SET senha = ?
                        WHERE nome = ?
                    """, (senha, usuario["equipe"]))

            conn.commit()
            conn.close()

            usuario = obter_usuario(login_usuario)
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

    return render_template("equipes.html", equipes=listar_equipes_dict())


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

        equipe_existente = obter_equipe(nome_equipe)
        if equipe_existente:
            erro = "Já existe uma equipe com esse nome."
            return render_template(
                "nova_equipe.html",
                erro=erro,
                sucesso=sucesso,
                dados_gerados=dados_gerados
            )

        logins_existentes = listar_logins_existentes()
        login_gerado = gerar_login_equipe(nome_equipe, logins_existentes)
        senha_gerada = gerar_senha_automatica()

        conn = conectar()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO equipes (nome, login, senha)
            VALUES (?, ?, ?)
        """, (nome_equipe, login_gerado, senha_gerada))

        cur.execute("""
            INSERT INTO usuarios (login, nome, senha, perfil, ativo, equipe)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (login_gerado, nome_equipe, senha_gerada, "equipe", 1, nome_equipe))

        conn.commit()
        conn.close()

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
# APROVAÇÕES - ORGANIZADOR / SUPERADMIN
# =========================================================
@app.route("/aprovacoes", methods=["GET", "POST"])
def aprovacoes():
    if not exige_login():
        return redirect(url_for("login"))

    if not exige_perfil(["superadmin", "organizador"]):
        return redirect(url_for("index"))

    sucesso = None
    erro = None

    if request.method == "POST":
        acao = request.form.get("acao", "").strip()
        equipe_nome = request.form.get("equipe", "").strip()
        cpf = limpar_cpf(request.form.get("cpf", "").strip())

        conn = conectar()
        cur = conn.cursor()

        if acao in ["aprovar", "rejeitar"]:
            novo_status = "aprovado" if acao == "aprovar" else "rejeitado"
            cur.execute("""
                UPDATE atletas
                SET status = ?
                WHERE equipe_nome = ? AND cpf = ?
            """, (novo_status, equipe_nome, cpf))

            if cur.rowcount > 0:
                sucesso = "Atleta atualizado com sucesso."
            else:
                erro = "Atleta não encontrado."

        elif acao == "excluir":
            cur.execute("""
                DELETE FROM atletas
                WHERE equipe_nome = ? AND cpf = ?
            """, (equipe_nome, cpf))

            if cur.rowcount > 0:
                sucesso = "Atleta excluído com sucesso."
            else:
                erro = "Atleta não encontrado para exclusão."

        conn.commit()
        conn.close()

    return render_template(
        "aprovacoes.html",
        equipes=listar_equipes_dict(),
        sucesso=sucesso,
        erro=erro
    )


# =========================================================
# LISTAGEM OFICIAL - SÓ APROVADOS
# =========================================================
@app.route("/listagem-oficial")
def listagem_oficial():
    if not exige_login():
        return redirect(url_for("login"))

    equipes = listar_equipes_dict()
    equipes_filtradas = {}

    for nome_eq, equipe in equipes.items():
        atletas_aprovados = [
            atleta for atleta in equipe.get("atletas", [])
            if atleta.get("status") == "aprovado"
        ]

        if atletas_aprovados:
            equipes_filtradas[nome_eq] = {
                "nome": nome_eq,
                "atletas": atletas_aprovados
            }

    return render_template(
        "listagem_oficial.html",
        equipes=equipes_filtradas
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

    nome_equipe = equipe_atual()

    if not nome_equipe:
        return redirect(url_for("logout"))

    equipe = obter_equipe(nome_equipe)

    if not equipe:
        return redirect(url_for("logout"))

    erro = None
    sucesso = None

    if request.method == "POST":
        acao = request.form.get("acao", "").strip()

        if acao == "excluir":
            cpf = limpar_cpf(request.form.get("cpf", "").strip())

            conn = conectar()
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM atletas
                WHERE equipe_nome = ? AND cpf = ?
            """, (nome_equipe, cpf))
            conn.commit()
            removidos = cur.rowcount
            conn.close()

            if removidos > 0:
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
                cpf_normalizado = limpar_cpf(cpf)

                if not cpf_valido(cpf_normalizado):
                    erro = "CPF inválido."
                else:
                    conn = conectar()
                    cur = conn.cursor()

                    cur.execute("""
                        SELECT equipe_nome, nome
                        FROM atletas
                        WHERE cpf = ?
                    """, (cpf_normalizado,))
                    conflito = cur.fetchone()

                    if conflito:
                        if conflito["equipe_nome"] == nome_equipe:
                            erro = "Este CPF já está cadastrado nesta equipe."
                        else:
                            erro = f"Este CPF já está cadastrado na equipe {conflito['equipe_nome']} ({conflito['nome']})."
                    else:
                        cur.execute("""
                            INSERT INTO atletas (
                                equipe_nome, nome, numero, cpf, data_nascimento, status
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            nome_equipe,
                            nome,
                            numero,
                            cpf_normalizado,
                            data_nascimento,
                            "pendente"
                        ))
                        conn.commit()
                        sucesso = "Atleta cadastrado com sucesso."

                    conn.close()

    equipe = obter_equipe(nome_equipe)

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