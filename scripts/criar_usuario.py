"""
Cria (ou atualiza a senha de) um usuário de login do sistema.

Não existe cadastro público de propósito — são só duas ou três pessoas
usando o sistema, e criar uma tela de cadastro pra isso seria
over-engineering. Rode este script localmente, uma vez por pessoa:

    python scripts/criar_usuario.py

A senha é digitada com getpass (não aparece na tela, não fica salva no
histórico do terminal).
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.auth import hash_senha
from app.database import SessionLocal
from app.models import Usuario


def main() -> None:
    username = input("Nome de usuário (login): ").strip()
    if not username:
        print("Nome de usuário não pode ficar em branco.")
        return

    nome = input("Nome de exibição (ex: Marçal, Seu Zé): ").strip()
    if not nome:
        print("Nome de exibição não pode ficar em branco.")
        return

    senha = getpass.getpass("Senha: ")
    if len(senha) < 6:
        print("Senha muito curta — use pelo menos 6 caracteres.")
        return
    confirmacao = getpass.getpass("Confirme a senha: ")
    if senha != confirmacao:
        print("As senhas não bateram.")
        return

    db = SessionLocal()
    try:
        usuario = db.scalar(select(Usuario).where(Usuario.username == username))
        if usuario:
            usuario.senha_hash = hash_senha(senha)
            usuario.nome = nome
            usuario.ativo = True
            db.commit()
            print(f"Senha atualizada para o usuário existente '{username}'.")
        else:
            db.add(Usuario(username=username, senha_hash=hash_senha(senha), nome=nome))
            db.commit()
            print(f"Usuário '{username}' criado com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
