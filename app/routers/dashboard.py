from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Despesa, FechamentoCaixa, Pagamento
from app.templating import templates

router = APIRouter(tags=["dashboard"])


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    hoje = date.today()

    pagamentos_hoje = db.scalars(select(Pagamento).where(Pagamento.data == hoje)).all()
    despesas_hoje = db.scalars(select(Despesa).where(Despesa.data == hoje)).all()

    # Agrupado em Python (não em SQL) de propósito: junta dado de duas
    # tabelas diferentes (pagamentos e despesas), e o volume de lançamentos
    # por dia numa padaria é baixo — não compensa a complexidade de um JOIN.
    saidas_por_forma: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for pagamento in pagamentos_hoje:
        saidas_por_forma[pagamento.forma_pagamento.nome] += pagamento.valor
    for despesa in despesas_hoje:
        saidas_por_forma[despesa.forma_pagamento.nome] += despesa.valor

    total_saidas_hoje = sum(saidas_por_forma.values(), Decimal("0"))
    # Regra de negócio (CLAUDE.md seção 4): só Dinheiro afeta o caixa físico.
    # Esse total é do DIA (calendário) inteiro, só informativo — o "Saldo
    # estimado" abaixo usa um recorte diferente (desde o último fechamento),
    # não esse valor.
    saidas_dinheiro_hoje = saidas_por_forma.get("Dinheiro", Decimal("0"))

    # Fundo de caixa = cédulas de troco do fechamento mais recente, seja de
    # hoje ou de um dia anterior (antes só pegava fechamento ANTES de hoje;
    # o usuário quer ver o mais recente de verdade, incluindo o de hoje de
    # manhã, por exemplo). Desempate por turno (Noite > Manhã) e por
    # criado_em, não pela ordem em que foram cadastrados — importante pra
    # não pegar o fechamento errado se um dia ele lançar fora de ordem.
    turno_ordem = case((FechamentoCaixa.turno == "Noite", 1), else_=0)
    ultimo_fechamento = db.scalar(
        select(FechamentoCaixa)
        .order_by(
            FechamentoCaixa.data.desc(), turno_ordem.desc(), FechamentoCaixa.criado_em.desc()
        )
        .limit(1)
    )
    fundo_inicial = ultimo_fechamento.cedulas_troco if ultimo_fechamento else None

    # Saldo estimado = fundo do último fechamento MENOS só as saídas em
    # dinheiro lançadas DEPOIS desse fechamento (não o dia inteiro).
    # Importante: se usássemos "saidas_dinheiro_hoje" aqui, um gasto feito
    # antes do fechamento da manhã seria descontado duas vezes — uma vez
    # porque já não está mais no troco contado, outra porque ainda entra
    # na soma do dia.
    saldo_estimado = None
    if ultimo_fechamento is not None:
        pagamentos_depois = db.scalars(
            select(Pagamento).where(Pagamento.criado_em > ultimo_fechamento.criado_em)
        ).all()
        despesas_depois = db.scalars(
            select(Despesa).where(Despesa.criado_em > ultimo_fechamento.criado_em)
        ).all()
        saidas_dinheiro_desde_fechamento = sum(
            (p.valor for p in pagamentos_depois if p.forma_pagamento.nome == "Dinheiro"),
            Decimal("0"),
        ) + sum(
            (d.valor for d in despesas_depois if d.forma_pagamento.nome == "Dinheiro"),
            Decimal("0"),
        )
        saldo_estimado = fundo_inicial - saidas_dinheiro_desde_fechamento

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "hoje": hoje,
            "saidas_por_forma": dict(saidas_por_forma),
            "total_saidas_hoje": total_saidas_hoje,
            "ultimo_fechamento": ultimo_fechamento,
            "fundo_inicial": fundo_inicial,
            "saidas_dinheiro_hoje": saidas_dinheiro_hoje,
            "saldo_estimado": saldo_estimado,
        },
    )
