from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FormaPagamento(Base):
    """
    Tabela de apoio (lookup): Dinheiro, Pix, e futuramente Débito/Crédito.

    Existe como tabela, e não como um valor fixo no código, porque já sabemos
    que essa lista vai crescer quando implementarmos Vendas no futuro.
    """

    __tablename__ = "formas_pagamento"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<FormaPagamento {self.nome}>"
