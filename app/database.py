"""
Configuração do SQLAlchemy: engine (conexão com o banco), fábrica de sessões
e a classe Base da qual todos os modelos (tabelas) vão herdar.

`get_db` é uma dependency do FastAPI: cada requisição ganha sua própria sessão
de banco, que é sempre fechada no final (mesmo se der erro no meio).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
