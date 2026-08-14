from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Funcionario(Base):
    __tablename__ = "funcionarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    # Soft delete: em vez de apagar o funcionário (o que quebraria o
    # histórico de pagamentos dele), marcamos como inativo.
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pagamentos: Mapped[list["Pagamento"]] = relationship(back_populates="funcionario")

    def __repr__(self) -> str:
        return f"<Funcionario {self.nome}>"
