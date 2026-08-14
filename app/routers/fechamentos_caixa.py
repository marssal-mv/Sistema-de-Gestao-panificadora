import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FechamentoCaixa

router = APIRouter(prefix="/fechamentos-caixa", tags=["fechamentos_caixa"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


@router.get("")
def listar(request: Request, db: Session = Depends(get_db)):
    fechamentos = db.scalars(
        select(FechamentoCaixa).order_by(FechamentoCaixa.data.desc())
    ).all()
    return templates.TemplateResponse(
        request, "fechamentos_caixa/lista.html", {"fechamentos": fechamentos}
    )


@router.get("/novo")
def form_novo(request: Request):
    return templates.TemplateResponse(
        request,
        "fechamentos_caixa/form.html",
        {"valores": {"data": date.today().isoformat()}},
    )


@router.post("")
def criar(
    request: Request,
    data: str = Form(...),
    cedulas_troco: str = Form(...),
    cedulas_inteiro: str = Form(...),
    observacao: str = Form(""),
    db: Session = Depends(get_db),
):
    erro = None
    data_valor: date | None = None
    troco_decimal: Decimal | None = None
    inteiro_decimal: Decimal | None = None

    try:
        data_valor = date.fromisoformat(data)
    except ValueError:
        erro = "Data inválida."

    if erro is None:
        try:
            troco_decimal = Decimal(cedulas_troco.replace(",", "."))
            if troco_decimal < 0:
                erro = "Cédulas de troco não pode ser negativo."
        except InvalidOperation:
            erro = "Valor de cédulas de troco inválido."

    if erro is None:
        try:
            inteiro_decimal = Decimal(cedulas_inteiro.replace(",", "."))
            if inteiro_decimal < 0:
                erro = "Cédulas inteiro não pode ser negativo."
        except InvalidOperation:
            erro = "Valor de cédulas inteiro inválido."

    if erro is None and db.scalar(
        select(FechamentoCaixa).where(FechamentoCaixa.data == data_valor)
    ):
        erro = "Já existe um fechamento de caixa registrado para essa data."

    if erro:
        return templates.TemplateResponse(
            request,
            "fechamentos_caixa/form.html",
            {
                "erro": erro,
                "valores": {
                    "data": data,
                    "cedulas_troco": cedulas_troco,
                    "cedulas_inteiro": cedulas_inteiro,
                    "observacao": observacao,
                },
            },
            status_code=422,
        )

    fechamento = FechamentoCaixa(
        data=data_valor,
        cedulas_troco=troco_decimal,
        cedulas_inteiro=inteiro_decimal,
        observacao=observacao.strip() or None,
    )
    db.add(fechamento)
    db.commit()
    logger.info(
        "Fechamento de caixa registrado: id=%s data=%s troco=%s inteiro=%s total=%s",
        fechamento.id,
        data_valor,
        troco_decimal,
        inteiro_decimal,
        fechamento.total,
    )
    return RedirectResponse("/fechamentos-caixa", status_code=303)
