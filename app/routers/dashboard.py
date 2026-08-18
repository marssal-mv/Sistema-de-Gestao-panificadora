from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Despesa, FechamentoCaixa, Pagamento

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


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
    saidas_dinheiro_hoje = saidas_por_forma.get("Dinheiro", Decimal("0"))

    # Fundo de caixa do dia = cédulas de troco do último fechamento antes de
    # hoje (confirmado com o usuário: o caixa sempre abre com o troco que
    # sobrou do fechamento anterior, não um valor fixo definido à parte).
    ultimo_fechamento = db.scalar(
        select(FechamentoCaixa)
        .where(FechamentoCaixa.data < hoje)
        .order_by(FechamentoCaixa.data.desc())
        .limit(1)
    )
    fundo_inicial = ultimo_fechamento.cedulas_troco if ultimo_fechamento else None
    saldo_estimado = (
        fundo_inicial - saidas_dinheiro_hoje if fundo_inicial is not None else None
    )

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
