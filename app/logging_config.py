"""
Configuração central de logging da aplicação.

Usa só a biblioteca padrão do Python (`logging`) — sem dependência nova.
Todo módulo do projeto usa `logging.getLogger(__name__)`, e como o pacote
se chama `app`, o nome de cada logger fica tipo "app.routers.pagamentos".
Isso os torna filhos do logger "app" configurado aqui, então basta
configurar os handlers uma vez, neste único lugar.

Dois destinos pros logs:
- Console: útil enquanto se está rodando `uvicorn --reload` e olhando o
  terminal.
- Arquivo rotativo em logs/app.log: útil pra olhar depois, sem precisar
  ter visto o terminal no momento exato do erro. Rotaciona em 5MB, mantém
  3 arquivos antigos, pra não crescer sem limite.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"

FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(level: str = "INFO") -> None:
    LOG_DIR.mkdir(exist_ok=True)

    # O codepage padrão do console do Windows não é UTF-8, o que corrompia
    # acentos nos logs (ex: "Aplicação" virava "Aplica��o"). Isso não afeta
    # o arquivo de log (já era UTF-8 explícito), só a tela do terminal.
    # StreamHandler sem argumento escreve no stderr, não no stdout — os dois
    # precisam ser reconfigurados.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    formatter = logging.Formatter(FORMATO, datefmt="%Y-%m-%d %H:%M:%S")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(level.upper())
    app_logger.handlers.clear()
    app_logger.addHandler(console_handler)
    app_logger.addHandler(file_handler)
    # Sem propagate, os logs não passam pro root logger e não duplicam
    # (o próprio uvicorn configura o root com seus handlers de acesso).
    app_logger.propagate = False
