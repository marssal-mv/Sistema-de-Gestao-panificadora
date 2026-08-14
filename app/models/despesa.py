from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Despesa(Base):
    """Compra/gasto da padaria (insumos, fornecedores, manutenção, etc.)."""

    __tablename__ = "despesas"
    __table_args__ = (CheckConstraint("valor > 0", name="ck_despesas_valor_positivo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    # Texto livre por enquanto (ex: "Rosivan"). Se um dia precisarmos de
    # relatórios por fornecedor, migramos isso para uma tabela própria.
    fornecedor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Opcional: o pai não categoriza no caderno, então não obrigamos aqui.
    categoria: Mapped[str | None] = mapped_column(String(60), nullable=True)
    forma_pagamento_id: Mapped[int] = mapped_column(ForeignKey("formas_pagamento.id"), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    forma_pagamento: Mapped["FormaPagamento"] = relationship()

    def __repr__(self) -> str:
        return f"<Despesa {self.descricao} valor={self.valor}>"
