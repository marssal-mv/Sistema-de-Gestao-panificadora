import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verificar_senha
from app.database import get_db
from app.models import Usuario
from app.templating import templates

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/login")
def form_login(request: Request):
    if request.session.get("usuario"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db),
):
    erro = "Usuário ou senha inválidos."
    usuario = db.scalar(select(Usuario).where(Usuario.username == username.strip()))

    if usuario is not None and usuario.ativo and verificar_senha(senha, usuario.senha_hash):
        request.session["usuario"] = {
            "id": usuario.id,
            "username": usuario.username,
            "nome": usuario.nome,
        }
        logger.info("Login bem-sucedido: username=%r", usuario.username)
        return RedirectResponse("/", status_code=303)

    logger.warning("Tentativa de login inválida: username=%r", username)
    return templates.TemplateResponse(
        request, "login.html", {"erro": erro}, status_code=401
    )


@router.post("/logout")
def logout(request: Request):
    usuario = request.session.get("usuario")
    request.session.clear()
    if usuario:
        logger.info("Logout: username=%r", usuario.get("username"))
    return RedirectResponse("/login", status_code=303)
