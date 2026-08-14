from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Pagamento(Base):
    """Pagamento feito a um funcionário (salário, adiantamento, vale, etc.)."""

    __tablename__ = "pagamentos"
    __table_args__ = (CheckConstraint("valor > 0", name="ck_pagamentos_valor_positivo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"), nullable=False)
    forma_pagamento_id: Mapped[int] = mapped_column(ForeignKey("formas_pagamento.id"), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    # Ex: "adiantamento para açaí" — o destino/motivo, como vimos nas fotos do caderno.
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    funcionario: Mapped["Funcionario"] = relationship(back_populates="pagamentos")
    forma_pagamento: Mapped["FormaPagamento"] = relationship()

    def __repr__(self) -> str:
        return f"<Pagamento funcionario_id={self.funcionario_id} valor={self.valor}>"
