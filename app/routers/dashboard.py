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
    saidas_dinheiro_hoje = saidas_por_forma.get("Dinheiro", Decimal("0"))

    # Totais separados por origem (Pagamento x Despesa), somando todas as
    # formas de pagamento juntas — diferente de saidas_por_forma, que
    # junta as duas origens mas separa por forma de pagamento.
    total_pagamentos_hoje = sum((p.valor for p in pagamentos_hoje), Decimal("0"))
    total_despesas_hoje = sum((d.valor for d in despesas_hoje), Decimal("0"))

    # Fundo de caixa = cédulas troco + cédulas inteiro do fechamento mais
    # recente (hoje ou de um dia anterior) — as duas categorias servem pra
    # dar troco (confirmado com o dono da padaria; a suposição inicial, de
    # que só "troco" contava, veio de uma leitura errada dos cadernos).
    # Desempate por turno (Noite > Manhã) e por criado_em, não pela ordem
    # em que foram cadastrados — importante pra não pegar o fechamento
    # errado se um dia ele lançar fora de ordem.
    #
    # Não existe mais um "saldo estimado do caixa" aqui: sem registro de
    # vendas, essa conta (fundo − saídas) só cresce negativa ao longo do
    # dia, porque nunca soma o dinheiro que realmente entra. Removido
    # depois de confirmar isso na prática — reintroduzir só quando /se o
    # sistema passar a registrar vendas.
    turno_ordem = case((FechamentoCaixa.turno == "Noite", 1), else_=0)
    ultimo_fechamento = db.scalar(
        select(FechamentoCaixa)
        .order_by(
            FechamentoCaixa.data.desc(), turno_ordem.desc(), FechamentoCaixa.criado_em.desc()
        )
        .limit(1)
    )
    fundo_inicial = ultimo_fechamento.total if ultimo_fechamento else None

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
            "total_pagamentos_hoje": total_pagamentos_hoje,
            "total_despesas_hoje": total_despesas_hoje,
        },
    )
