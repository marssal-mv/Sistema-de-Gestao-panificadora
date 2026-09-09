"""
Importar todos os modelos aqui garante que, quando alguém importar
`app.models`, o SQLAlchemy (e o Alembic) já conheçam todas as tabelas.
Sem isso, é fácil esquecer de importar um modelo novo e o Alembic não
detectar a tabela ao gerar uma migration automática.
"""

from app.models.forma_pagamento import FormaPagamento
from app.models.funcionario import Funcionario
from app.models.pagamento import Pagamento
from app.models.despesa import Despesa
from app.models.fechamento_caixa import TURNOS_VALIDOS, FechamentoCaixa
from app.models.usuario import Usuario

__all__ = [
    "FormaPagamento",
    "Funcionario",
    "Pagamento",
    "Despesa",
    "FechamentoCaixa",
    "TURNOS_VALIDOS",
    "Usuario",
]
