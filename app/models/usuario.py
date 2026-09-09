from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Usuario(Base):
    """
    Login do sistema (poucos usuários — quem desenvolve e o dono da
    padaria). Sem cadastro público: contas são criadas via
    `scripts/criar_usuario.py`, rodado localmente por quem já tem acesso
    ao servidor.
    """

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    # Soft delete, mesmo padrão de Funcionário: revogar acesso sem apagar
    # o usuário (evita perder rastro de quem fez o quê, se algum dia
    # tivermos log de autoria por lançamento).
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Usuario {self.username}>"
