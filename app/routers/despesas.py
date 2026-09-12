import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, HTTPException, Request
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
    mostrar_todos: bool = False,
    db: Session = Depends(get_db),
):
    query = select(Despesa).order_by(Despesa.data.desc(), Despesa.id.desc())
    # Sem nenhum filtro explícito, mostra só hoje — pra não misturar tudo
    # numa lista só e confundir o usuário. "Mostrar dias anteriores" ou
    # escolher uma data no filtro tira essa restrição.
    somente_hoje = not mostrar_todos and not data_inicio and not data_fim
    if somente_hoje:
        query = query.where(Despesa.data == date.today())
    else:
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
            "somente_hoje": somente_hoje,
            "hoje": date.today(),
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


@router.get("/{despesa_id}/editar")
def form_editar(despesa_id: int, request: Request, db: Session = Depends(get_db)):
    despesa = db.get(Despesa, despesa_id)
    if despesa is None:
        logger.warning("Tentativa de editar despesa inexistente: id=%s", despesa_id)
        raise HTTPException(status_code=404, detail="Despesa não encontrada")
    formas_pagamento = db.scalars(select(FormaPagamento).order_by(FormaPagamento.nome)).all()
    return templates.TemplateResponse(
        request,
        "despesas/form.html",
        {
            "despesa": despesa,
            "formas_pagamento": formas_pagamento,
            "valores": {
                "descricao": despesa.descricao,
                "forma_pagamento_id": despesa.forma_pagamento_id,
                "valor": str(despesa.valor),
                "data": despesa.data.isoformat(),
                "observacao": despesa.observacao,
            },
        },
    )


@router.post("/{despesa_id}/editar")
def editar(
    despesa_id: int,
    request: Request,
    descricao: str = Form(...),
    forma_pagamento_id: int = Form(...),
    valor: str = Form(...),
    data: str = Form(...),
    observacao: str = Form(""),
    db: Session = Depends(get_db),
):
    despesa = db.get(Despesa, despesa_id)
    if despesa is None:
        logger.warning("Tentativa de editar despesa inexistente: id=%s", despesa_id)
        raise HTTPException(status_code=404, detail="Despesa não encontrada")

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
            "Tentativa de editar despesa com forma de pagamento inexistente: id=%s",
            forma_pagamento_id,
        )

    if erro:
        formas_pagamento = db.scalars(select(FormaPagamento).order_by(FormaPagamento.nome)).all()
        return templates.TemplateResponse(
            request,
            "despesas/form.html",
            {
                "despesa": despesa,
                "formas_pagamento": formas_pagamento,
                "erro": erro,
                "valores": {
                    "descricao": descricao,
                    "forma_pagamento_id": forma_pagamento_id,
                    "valor": valor,
                    "data": data,
                    "observacao": observacao,
                },
            },
            status_code=422,
        )

    valor_antigo = despesa.valor
    despesa.descricao = descricao
    # fornecedor/categoria não são mais editáveis por aqui — quem já tinha
    # valor preenchido (ex: id=2 "Rosivan") mantém intacto no banco, só não
    # aparece mais na tela nem pode ser alterado por essa rota.
    despesa.forma_pagamento_id = forma_pagamento_id
    despesa.valor = valor_decimal
    despesa.data = data_valor
    despesa.observacao = observacao.strip() or None
    db.commit()
    logger.info(
        "Despesa atualizada: id=%s descricao=%r valor_antigo=%s valor_novo=%s",
        despesa.id,
        despesa.descricao,
        valor_antigo,
        valor_decimal,
    )
    return RedirectResponse("/despesas", status_code=303)
