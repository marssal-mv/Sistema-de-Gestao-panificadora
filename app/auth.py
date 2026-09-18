"""
Funções de autenticação: hash/verificação de senha (bcrypt puro, sem
passlib — passlib está sem manutenção desde 2020 e quebra com versões
recentes do bcrypt) e leitura do usuário logado a partir
da sessão (cookie assinado, via SessionMiddleware do Starlette).
"""

import bcrypt
from fastapi import Request


def hash_senha(senha: str) -> str:
    hash_bytes = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())
    return hash_bytes.decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def usuario_logado(request: Request) -> dict | None:
    """Retorna {"id": ..., "username": ..., "nome": ...} ou None."""
    return request.session.get("usuario")
