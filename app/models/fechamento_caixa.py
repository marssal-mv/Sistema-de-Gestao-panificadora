from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FechamentoCaixa(Base):
    """
    Fechamento diário do caixa físico.

    `total` não existe como coluna: é sempre cedulas_troco + cedulas_inteiro,
    calculado na hora da consulta, para não correr o risco de ficar
    desatualizado em relação aos dois valores que realmente importam.
    """

    __tablename__ = "fechamentos_caixa"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    cedulas_troco: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    cedulas_inteiro: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @property
    def total(self) -> Decimal:
        return self.cedulas_troco + self.cedulas_inteiro

    def __repr__(self) -> str:
        return f"<FechamentoCaixa {self.data} total={self.total}>"
