# Sistema Pra Padaria — Panificadora Rosa de Saron

Sistema de gestão para substituir os cadernos de controle manual da padaria.
Contexto completo do projeto, levantamento de requisitos e decisões de
arquitetura estão no documento "levantamento de requisitos - fase 1" do
projeto Claude "Sistema Pra Padaria".

## Estrutura do projeto

```
app/
  main.py           # cria a aplicação FastAPI e registra as rotas
  config.py         # lê variáveis de ambiente (.env) de forma tipada
  database.py       # engine do SQLAlchemy, sessão, Base dos modelos
  models/           # um arquivo por tabela (funcionário, pagamento, despesa, ...)
  routers/          # rotas da aplicação, agrupadas por funcionalidade (vazio por enquanto)
  templates/        # páginas HTML (Jinja2), com base.html sendo o layout comum
  static/           # CSS/JS/imagens servidos diretamente
alembic/            # histórico versionado de mudanças no schema do banco
docker-compose.yml  # sobe um PostgreSQL local para desenvolvimento
```

## Como rodar localmente

1. Criar e ativar um ambiente virtual Python:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Instalar as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Copiar `.env.example` para `.env` e ajustar se necessário.
4. Subir o banco de dados local (requer Docker):
   ```
   docker compose up -d
   ```
5. Aplicar as migrations (cria as tabelas no banco):
   ```
   alembic upgrade head
   ```
6. Rodar a aplicação:
   ```
   uvicorn app.main:app --reload
   ```
7. Acessar http://localhost:8000

## Estado atual

Isso é só o esqueleto do projeto (passo 10 do plano): a aplicação sobe, se
conecta ao layout base e aos modelos já estão definidos, mas nenhuma
funcionalidade (cadastrar funcionário, registrar pagamento, etc.) foi
implementada ainda. Isso vem no próximo passo, uma de cada vez.
