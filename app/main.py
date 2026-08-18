"""
Ponto de entrada da aplicação FastAPI.

Registra os routers de cada funcionalidade, configura logging e tem um
handler global pra erros não tratados (loga a exceção completa e devolve
uma página genérica, sem vazar detalhes internos pra quem está usando).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.logging_config import setup_logging
from app.routers import dashboard, despesas, fechamentos_caixa, funcionarios, pagamentos
from app.templating import templates

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Aplicação iniciada")
    yield
    logger.info("Aplicação encerrada")


app = FastAPI(title="Sistema Pra Padaria", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(dashboard.router)
app.include_router(funcionarios.router)
app.include_router(pagamentos.router)
app.include_router(despesas.router)
app.include_router(fechamentos_caixa.router)


@app.exception_handler(Exception)
async def erro_nao_tratado(request: Request, _exc: Exception):
    logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return templates.TemplateResponse(request, "erro.html", {}, status_code=500)


@app.get("/healthz")
def healthz():
    """Usado para verificar rapidamente se a aplicação está de pé."""
    return {"status": "ok"}
