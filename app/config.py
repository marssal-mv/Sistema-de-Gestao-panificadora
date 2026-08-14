"""
Configurações da aplicação.

Usamos pydantic-settings para ler variáveis de ambiente (do arquivo .env)
de forma tipada. Assim, se esquecermos de definir DATABASE_URL, por exemplo,
a aplicação falha imediatamente ao subir, com uma mensagem clara — em vez de
falhar em algum lugar aleatório do código na primeira vez que alguém tentar
usar o banco.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    secret_key: str
    log_level: str = "INFO"


# Instância única, importada pelo resto da aplicação (padrão "settings singleton").
settings = Settings()
