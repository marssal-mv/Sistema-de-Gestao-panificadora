from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

TURNOS_VALIDOS = ("Manhã", "Noite")


class FechamentoCaixa(Base):
    """
    Fechamento do caixa físico, feito duas vezes por dia (manhã e noite).

    `total` não existe como coluna: é sempre cedulas_troco + cedulas_inteiro,
    calculado na hora da consulta, para não correr o risco de ficar
    desatualizado em relação aos dois valores que realmente importam.
    """

    __tablename__ = "fechamentos_caixa"
    __table_args__ = (
        UniqueConstraint("data", "turno", name="uq_fechamentos_caixa_data_turno"),
        CheckConstraint("turno IN ('Manhã', 'Noite')", name="ck_fechamentos_caixa_turno_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    turno: Mapped[str] = mapped_column(String(10), nullable=False)
    cedulas_troco: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    cedulas_inteiro: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @property
    def total(self) -> Decimal:
        return self.cedulas_troco + self.cedulas_inteiro

    def __repr__(self) -> str:
        return f"<FechamentoCaixa {self.data} {self.turno} total={self.total}>"
