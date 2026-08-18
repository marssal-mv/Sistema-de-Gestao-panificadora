import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Funcionario
from app.templating import templates

router = APIRouter(prefix="/funcionarios", tags=["funcionarios"])
logger = logging.getLogger(__name__)


@router.get("")
def listar(request: Request, mostrar_inativos: bool = False, db: Session = Depends(get_db)):
    query = select(Funcionario).order_by(Funcionario.nome)
    if not mostrar_inativos:
        query = query.where(Funcionario.ativo.is_(True))
    funcionarios = db.scalars(query).all()
    return templates.TemplateResponse(
        request,
        "funcionarios/lista.html",
        {"funcionarios": funcionarios, "mostrar_inativos": mostrar_inativos},
    )


@router.get("/novo")
def form_novo(request: Request):
    return templates.TemplateResponse(request, "funcionarios/form.html", {"funcionario": None})


@router.post("")
def criar(request: Request, nome: str = Form(...), db: Session = Depends(get_db)):
    nome = nome.strip()
    if not nome:
        return templates.TemplateResponse(
            request,
            "funcionarios/form.html",
            {"funcionario": None, "erro": "Nome não pode ficar em branco."},
            status_code=422,
        )
    funcionario = Funcionario(nome=nome)
    db.add(funcionario)
    db.commit()
    logger.info("Funcionário cadastrado: id=%s nome=%r", funcionario.id, funcionario.nome)
    return RedirectResponse("/funcionarios", status_code=303)


@router.get("/{funcionario_id}/editar")
def form_editar(funcionario_id: int, request: Request, db: Session = Depends(get_db)):
    funcionario = db.get(Funcionario, funcionario_id)
    if funcionario is None:
        logger.warning("Tentativa de editar funcionário inexistente: id=%s", funcionario_id)
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    return templates.TemplateResponse(
        request, "funcionarios/form.html", {"funcionario": funcionario}
    )


@router.post("/{funcionario_id}/editar")
def editar(
    funcionario_id: int, request: Request, nome: str = Form(...), db: Session = Depends(get_db)
):
    funcionario = db.get(Funcionario, funcionario_id)
    if funcionario is None:
        logger.warning("Tentativa de editar funcionário inexistente: id=%s", funcionario_id)
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    nome = nome.strip()
    if not nome:
        return templates.TemplateResponse(
            request,
            "funcionarios/form.html",
            {"funcionario": funcionario, "erro": "Nome não pode ficar em branco."},
            status_code=422,
        )
    funcionario.nome = nome
    db.commit()
    logger.info("Funcionário atualizado: id=%s nome_novo=%r", funcionario.id, funcionario.nome)
    return RedirectResponse("/funcionarios", status_code=303)


@router.post("/{funcionario_id}/inativar")
def inativar(funcionario_id: int, db: Session = Depends(get_db)):
    funcionario = db.get(Funcionario, funcionario_id)
    if funcionario is None:
        logger.warning("Tentativa de inativar funcionário inexistente: id=%s", funcionario_id)
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    funcionario.ativo = False
    db.commit()
    logger.info("Funcionário inativado: id=%s nome=%r", funcionario.id, funcionario.nome)
    return RedirectResponse("/funcionarios", status_code=303)


@router.post("/{funcionario_id}/ativar")
def ativar(funcionario_id: int, db: Session = Depends(get_db)):
    funcionario = db.get(Funcionario, funcionario_id)
    if funcionario is None:
        logger.warning("Tentativa de reativar funcionário inexistente: id=%s", funcionario_id)
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    funcionario.ativo = True
    db.commit()
    logger.info("Funcionário reativado: id=%s nome=%r", funcionario.id, funcionario.nome)
    return RedirectResponse("/funcionarios", status_code=303)
