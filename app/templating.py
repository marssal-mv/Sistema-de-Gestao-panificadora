"""
Instância compartilhada do Jinja2Templates, usada por main.py e por todos
os routers.

Importante usar UMA instância só (em vez de cada arquivo criar a sua):
globals registrados no Environment do Jinja (como cache_bust, abaixo) só
valem pra quem usa essa mesma instância. Com instâncias separadas, cada
router "não conhece" os globals registrados em outro lugar.
"""

import os

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def cache_bust(static_url: str) -> str:
    """
    Adiciona ?v=<data de modificação> a uma URL /static/..., pra forçar o
    navegador a buscar a versão nova sempre que o arquivo mudar, em vez de
    continuar servindo uma versão antiga guardada em cache.
    """
    relative_path = static_url.removeprefix("/static/")
    full_path = os.path.join("app", "static", relative_path)
    try:
        version = int(os.path.getmtime(full_path))
    except OSError:
        return static_url
    return f"{static_url}?v={version}"


templates.env.globals["cache_bust"] = cache_bust
