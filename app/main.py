"""
Ponto de entrada da aplicação FastAPI.

Por enquanto só sobe o esqueleto: uma rota de dashboard (placeholder) e uma
rota de healthcheck. As rotas de verdade (funcionários, despesas, caixa)
entram no próximo passo do plano, uma funcionalidade por vez.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import funcionarios

app = FastAPI(title="Sistema Pra Padaria")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(funcionarios.router)


@app.get("/healthz")
def healthz():
    """Usado para verificar rapidamente se a aplicação está de pé."""
    return {"status": "ok"}


@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")
