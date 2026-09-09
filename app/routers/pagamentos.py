import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, HTTPException, Request
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
    funcionario_id: str = "",
    data_inicio: str = "",
    data_fim: str = "",
    mostrar_todos: bool = False,
    db: Session = Depends(get_db),
):
    # Recebido como string, não int direto: a opção "Todos" do <select>
    # manda funcionario_id="" (string vazia), que o FastAPI não converte
    # sozinho pra int — daria 422 automático (JSON cru, sem estilo nenhum)
    # toda vez que alguém filtrasse com "Todos" selecionado, que é o
    # padrão da tela.
    funcionario_id_filtro = int(funcionario_id) if funcionario_id else None

    query = select(Pagamento).order_by(Pagamento.data.desc(), Pagamento.id.desc())
    # Sem nenhum filtro explícito, mostra só hoje — pra não misturar tudo
    # numa lista só e confundir o usuário. Escolher um funcionário, uma
    # data, ou "Mostrar dias anteriores" tira essa restrição.
    somente_hoje = (
        not mostrar_todos
        and funcionario_id_filtro is None
        and not data_inicio
        and not data_fim
    )
    if somente_hoje:
        query = query.where(Pagamento.data == date.today())
    else:
        if funcionario_id_filtro:
            query = query.where(Pagamento.funcionario_id == funcionario_id_filtro)
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
            "filtro_funcionario_id": funcionario_id_filtro,
            "filtro_data_inicio": data_inicio,
            "filtro_data_fim": data_fim,
            "somente_hoje": somente_hoje,
            "hoje": date.today(),
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


@router.get("/{pagamento_id}/editar")
def form_editar(pagamento_id: int, request: Request, db: Session = Depends(get_db)):
    pagamento = db.get(Pagamento, pagamento_id)
    if pagamento is None:
        logger.warning("Tentativa de editar pagamento inexistente: id=%s", pagamento_id)
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    # Inclui inativos aqui (diferente do form de criar): o pagamento pode já
    # ter sido feito a um funcionário que saiu depois, e o select precisa
    # conseguir mostrar a seleção atual mesmo assim.
    funcionarios = db.scalars(select(Funcionario).order_by(Funcionario.nome)).all()
    formas_pagamento = db.scalars(select(FormaPagamento).order_by(FormaPagamento.nome)).all()
    return templates.TemplateResponse(
        request,
        "pagamentos/form.html",
        {
            "pagamento": pagamento,
            "funcionarios": funcionarios,
            "formas_pagamento": formas_pagamento,
            "valores": {
                "funcionario_id": pagamento.funcionario_id,
                "forma_pagamento_id": pagamento.forma_pagamento_id,
                "valor": str(pagamento.valor),
                "data": pagamento.data.isoformat(),
                "observacao": pagamento.observacao,
            },
        },
    )


@router.post("/{pagamento_id}/editar")
def editar(
    pagamento_id: int,
    request: Request,
    funcionario_id: int = Form(...),
    forma_pagamento_id: int = Form(...),
    valor: str = Form(...),
    data: str = Form(...),
    observacao: str = Form(""),
    db: Session = Depends(get_db),
):
    pagamento = db.get(Pagamento, pagamento_id)
    if pagamento is None:
        logger.warning("Tentativa de editar pagamento inexistente: id=%s", pagamento_id)
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

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
            "Tentativa de editar pagamento pra funcionário inexistente: id=%s",
            funcionario_id,
        )

    if erro is None and db.get(FormaPagamento, forma_pagamento_id) is None:
        erro = "Forma de pagamento não encontrada."
        logger.warning(
            "Tentativa de editar pagamento com forma de pagamento inexistente: id=%s",
            forma_pagamento_id,
        )

    if erro:
        funcionarios = db.scalars(select(Funcionario).order_by(Funcionario.nome)).all()
        formas_pagamento = db.scalars(select(FormaPagamento).order_by(FormaPagamento.nome)).all()
        return templates.TemplateResponse(
            request,
            "pagamentos/form.html",
            {
                "pagamento": pagamento,
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

    valor_antigo = pagamento.valor
    pagamento.funcionario_id = funcionario_id
    pagamento.forma_pagamento_id = forma_pagamento_id
    pagamento.valor = valor_decimal
    pagamento.data = data_valor
    pagamento.observacao = observacao.strip() or None
    db.commit()
    logger.info(
        "Pagamento atualizado: id=%s valor_antigo=%s valor_novo=%s",
        pagamento.id,
        valor_antigo,
        valor_decimal,
    )
    return RedirectResponse("/pagamentos", status_code=303)
