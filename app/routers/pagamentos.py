import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FormaPagamento, Funcionario, Pagamento
from app.templating import templates

router = APIRouter(prefix="/pagamentos", tags=["pagamentos"])
logger = logging.getLogger(__name__)


@router.get("")
def listar(
    request: Request,
    funcionario_id: int | None = None,
    data_inicio: str = "",
    data_fim: str = "",
    db: Session = Depends(get_db),
):
    query = select(Pagamento).order_by(Pagamento.data.desc(), Pagamento.id.desc())
    if funcionario_id:
        query = query.where(Pagamento.funcionario_id == funcionario_id)
    if data_inicio:
        query = query.where(Pagamento.data >= date.fromisoformat(data_inicio))
    if data_fim:
        query = query.where(Pagamento.data <= date.fromisoformat(data_fim))
    pagamentos = db.scalars(query).all()

    # Inclui inativos no filtro: pagamento a ex-funcionário continua no histórico.
    funcionarios = db.scalars(select(Funcionario).order_by(Funcionario.nome)).all()

    return templates.TemplateResponse(
        request,
        "pagamentos/lista.html",
        {
            "pagamentos": pagamentos,
            "funcionarios": funcionarios,
            "filtro_funcionario_id": funcionario_id,
            "filtro_data_inicio": data_inicio,
            "filtro_data_fim": data_fim,
        },
    )


@router.get("/novo")
def form_novo(request: Request, db: Session = Depends(get_db)):
    funcionarios = db.scalars(
        select(Funcionario).where(Funcionario.ativo.is_(True)).order_by(Funcionario.nome)
    ).all()
    formas_pagamento = db.scalars(select(FormaPagamento).order_by(FormaPagamento.nome)).all()
    return templates.TemplateResponse(
        request,
        "pagamentos/form.html",
        {
            "funcionarios": funcionarios,
            "formas_pagamento": formas_pagamento,
            "valores": {"data": date.today().isoformat()},
        },
    )


@router.post("")
def criar(
    request: Request,
    funcionario_id: int = Form(...),
    forma_pagamento_id: int = Form(...),
    valor: str = Form(...),
    data: str = Form(...),
    observacao: str = Form(""),
    db: Session = Depends(get_db),
):
    erro = None
    valor_decimal: Decimal | None = None
    data_valor: date | None = None

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

    if erro is None and db.get(Funcionario, funcionario_id) is None:
        erro = "Funcionário não encontrado."
        logger.warning(
            "Tentativa de registrar pagamento pra funcionário inexistente: id=%s",
            funcionario_id,
        )

    if erro is None and db.get(FormaPagamento, forma_pagamento_id) is None:
        erro = "Forma de pagamento não encontrada."
        logger.warning(
            "Tentativa de registrar pagamento com forma de pagamento inexistente: id=%s",
            forma_pagamento_id,
        )

    if erro:
        funcionarios = db.scalars(
            select(Funcionario).where(Funcionario.ativo.is_(True)).order_by(Funcionario.nome)
        ).all()
        formas_pagamento = db.scalars(select(FormaPagamento).order_by(FormaPagamento.nome)).all()
        return templates.TemplateResponse(
            request,
            "pagamentos/form.html",
            {
                "funcionarios": funcionarios,
                "formas_pagamento": formas_pagamento,
                "erro": erro,
                "valores": {
                    "funcionario_id": funcionario_id,
                    "forma_pagamento_id": forma_pagamento_id,
                    "valor": valor,
                    "data": data,
                    "observacao": observacao,
                },
            },
            status_code=422,
        )

    pagamento = Pagamento(
        funcionario_id=funcionario_id,
        forma_pagamento_id=forma_pagamento_id,
        valor=valor_decimal,
        data=data_valor,
        observacao=observacao.strip() or None,
    )
    db.add(pagamento)
    db.commit()
    logger.info(
        "Pagamento registrado: id=%s funcionario_id=%s forma_pagamento_id=%s valor=%s data=%s",
        pagamento.id,
        funcionario_id,
        forma_pagamento_id,
        valor_decimal,
        data_valor,
    )
    return RedirectResponse("/pagamentos", status_code=303)
