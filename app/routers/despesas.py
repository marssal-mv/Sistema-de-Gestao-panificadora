import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Despesa, FormaPagamento
from app.templating import templates

router = APIRouter(prefix="/despesas", tags=["despesas"])
logger = logging.getLogger(__name__)


@router.get("")
def listar(
    request: Request,
    data_inicio: str = "",
    data_fim: str = "",
    db: Session = Depends(get_db),
):
    query = select(Despesa).order_by(Despesa.data.desc(), Despesa.id.desc())
    if data_inicio:
        query = query.where(Despesa.data >= date.fromisoformat(data_inicio))
    if data_fim:
        query = query.where(Despesa.data <= date.fromisoformat(data_fim))
    despesas = db.scalars(query).all()

    return templates.TemplateResponse(
        request,
        "despesas/lista.html",
        {
            "despesas": despesas,
            "filtro_data_inicio": data_inicio,
            "filtro_data_fim": data_fim,
        },
    )


@router.get("/novo")
def form_novo(request: Request, db: Session = Depends(get_db)):
    formas_pagamento = db.scalars(select(FormaPagamento).order_by(FormaPagamento.nome)).all()
    return templates.TemplateResponse(
        request,
        "despesas/form.html",
        {
            "formas_pagamento": formas_pagamento,
            "valores": {"data": date.today().isoformat()},
        },
    )


@router.post("")
def criar(
    request: Request,
    descricao: str = Form(...),
    fornecedor: str = Form(""),
    categoria: str = Form(""),
    forma_pagamento_id: int = Form(...),
    valor: str = Form(...),
    data: str = Form(...),
    observacao: str = Form(""),
    db: Session = Depends(get_db),
):
    erro = None
    valor_decimal: Decimal | None = None
    data_valor: date | None = None
    descricao = descricao.strip()

    if not descricao:
        erro = "Descrição não pode ficar em branco."

    if erro is None:
        try:
            valor_decimal = Decimal(valor.replace(",", "."))
            if valor_decimal <= 0:
                erro = "Valor precisa ser maior que zero."
        except InvalidOperation:
            erro = "Valor inválido."

    if erro is None:
        try:
            data_valor = date.fromisoformat(data)
        except ValueError:
            erro = "Data inválida."

    if erro is None and db.get(FormaPagamento, forma_pagamento_id) is None:
        erro = "Forma de pagamento não encontrada."
        logger.warning(
            "Tentativa de registrar despesa com forma de pagamento inexistente: id=%s",
            forma_pagamento_id,
        )

    if erro:
        formas_pagamento = db.scalars(select(FormaPagamento).order_by(FormaPagamento.nome)).all()
        return templates.TemplateResponse(
            request,
            "despesas/form.html",
            {
                "formas_pagamento": formas_pagamento,
                "erro": erro,
                "valores": {
                    "descricao": descricao,
                    "fornecedor": fornecedor,
                    "categoria": categoria,
                    "forma_pagamento_id": forma_pagamento_id,
                    "valor": valor,
                    "data": data,
                    "observacao": observacao,
                },
            },
            status_code=422,
        )

    despesa = Despesa(
        descricao=descricao,
        fornecedor=fornecedor.strip() or None,
        categoria=categoria.strip() or None,
        forma_pagamento_id=forma_pagamento_id,
        valor=valor_decimal,
        data=data_valor,
        observacao=observacao.strip() or None,
    )
    db.add(despesa)
    db.commit()
    logger.info(
        "Despesa registrada: id=%s descricao=%r valor=%s data=%s",
        despesa.id,
        despesa.descricao,
        valor_decimal,
        data_valor,
    )
    return RedirectResponse("/despesas", status_code=303)
