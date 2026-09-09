# Sistema Pra Padaria — Panificadora Rosa de Saron

Sistema de gestão para substituir os cadernos de controle manual da padaria da
família. Contexto completo do levantamento de requisitos e decisões de
arquitetura está no [`CLAUDE.md`](CLAUDE.md).

## Objetivo e funcionamento geral

Hoje o controle diário da padaria (pagamentos a funcionários, despesas,
fechamento de caixa) é feito em caderno de papel. O sistema digitaliza esse
controle: cada funcionalidade do caderno vira uma tela simples, sem exigir
conhecimento técnico de quem usa (o usuário final real é o pai do
desenvolvedor, dono da padaria).

Não há controle de vendas/nota fiscal — a padaria não emite nota na maior
parte do atendimento, então isso é um projeto futuro separado, fora de escopo
por enquanto.

## Arquitetura e principais componentes

Monolito server-rendered: um único processo Python serve tanto as rotas de
dados quanto o HTML já pronto (sem frontend separado, sem API JSON pública).

| Camada | Tecnologia |
|---|---|
| Framework web | FastAPI |
| Banco de dados | PostgreSQL 16 (local via Docker) |
| ORM / migrations | SQLAlchemy 2.0 + Alembic |
| Templates | Jinja2 + Bootstrap 5 (via CDN) |
| Logging | biblioteca padrão `logging` (sem dependência extra) |
| Autenticação | usuário/senha (bcrypt) + sessão via cookie assinado (`itsdangerous`, usado pelo `SessionMiddleware` do Starlette) |

Por que monolito e não API + frontend separados: um único usuário (o pai),
sem necessidade de app mobile por enquanto — separar traria complexidade
(CORS, dois deploys) sem benefício real agora. Justificativas completas de
cada escolha de arquitetura estão no `CLAUDE.md`, seção 5.

## Estrutura de pastas

```
app/
  main.py             # cria o FastAPI app, registra routers/middlewares, logging, handler de erro global
  config.py           # Settings (pydantic-settings) — lê variáveis de ambiente do .env
  database.py         # engine do SQLAlchemy, SessionLocal, Base, dependency get_db()
  logging_config.py   # configuração central de logging (console + arquivo)
  templating.py       # instância compartilhada do Jinja2Templates (+ cache_bust)
  auth.py             # hash/verificação de senha (bcrypt) e leitura do usuário da sessão
  models/             # um arquivo por tabela (funcionário, pagamento, despesa, forma_pagamento, fechamento_caixa, usuário)
  routers/             # rotas da aplicação, um arquivo por funcionalidade (+ auth.py: login/logout)
  templates/           # páginas HTML (Jinja2); base.html é o layout comum;
                        # cada funcionalidade tem sua subpasta (ex: funcionarios/, pagamentos/)
  static/css/          # CSS customizado (Bootstrap vem do CDN) + paleta da marca
  static/img/           # logo e outros assets visuais
alembic/                # histórico versionado de mudanças no schema do banco
  versions/             # uma migration por mudança de schema
scripts/                 # scripts de manutenção rodados manualmente (ex: criar_usuario.py)
logs/                    # gerado em runtime (git-ignorado) — ver seção "Logs" abaixo
docker-compose.yml       # sobe um PostgreSQL local para desenvolvimento
requirements.txt         # dependências Python fixadas por versão exata
.env.example              # modelo de variáveis de ambiente — copiar para .env
```

## Tecnologias e dependências

Ver [`requirements.txt`](requirements.txt) para as versões exatas. Resumo do
que cada uma faz no projeto:

| Pacote | Papel |
|---|---|
| `fastapi` | framework web (rotas, validação de request, injeção de dependência) |
| `uvicorn[standard]` | servidor ASGI que roda a aplicação |
| `sqlalchemy` | ORM — mapeia classes Python para tabelas do Postgres |
| `alembic` | gera e aplica migrations (mudanças versionadas de schema) |
| `psycopg[binary]` | driver de conexão com o PostgreSQL (psycopg3) |
| `pydantic-settings` | leitura tipada de variáveis de ambiente (`app/config.py`) |
| `jinja2` | motor de templates HTML |
| `python-multipart` | necessário pro FastAPI ler dados de formulário (`Form(...)`) |
| `bcrypt` | hash/verificação de senha do login (usado direto, sem `passlib` — ver nota de compatibilidade abaixo) |
| `itsdangerous` | assina o cookie de sessão do login (`SessionMiddleware` do Starlette) |

**Nota de compatibilidade:** o projeto roda em Python 3.14 (recente).
Três dependências precisaram de ajuste por causa disso — ver `CLAUDE.md`
seção 7 e a entrada de 09/09/2026 pro histórico completo: troca de
`psycopg2-binary` por `psycopg[binary]`, `sqlalchemy` fixado em `2.0.52`
por um bug de tipagem, e `passlib` removido em favor do `bcrypt` puro
(passlib está sem manutenção desde 2020 e quebra com versões recentes
do bcrypt).

## Como executar localmente

1. Criar e ativar um ambiente virtual Python:
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1      # Windows PowerShell
   # ou: source .venv/bin/activate  # Linux/Mac
   ```
2. Instalar as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Copiar `.env.example` para `.env` e ajustar se necessário (ver seção
   seguinte).
4. Subir o banco de dados local (requer Docker Desktop rodando):
   ```
   docker compose up -d
   ```
5. Aplicar as migrations (cria as tabelas no banco):
   ```
   alembic upgrade head
   ```
6. Criar seu usuário de login (o sistema não tem cadastro público —
   veja a seção "Autenticação" abaixo):
   ```
   python scripts/criar_usuario.py
   ```
7. Rodar a aplicação:
   ```
   uvicorn app.main:app --reload
   ```
8. Acessar http://localhost:8000 — vai redirecionar pra `/login`

## Configurações e variáveis de ambiente

Definidas em `app/config.py`, lidas do arquivo `.env` (nunca commitado —
está no `.gitignore`). Ver `.env.example` para o modelo.

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `DATABASE_URL` | Sim | — | String de conexão SQLAlchemy com o Postgres. Formato: `postgresql+psycopg://usuario:senha@host:porta/banco` |
| `SECRET_KEY` | Sim | — | Chave pra assinar o cookie de sessão do login (`SessionMiddleware`). Trocar essa chave invalida todas as sessões ativas — todo mundo precisa logar de novo. Gerar com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `LOG_LEVEL` | Não | `INFO` | Nível de detalhe dos logs: `DEBUG`, `INFO`, `WARNING` ou `ERROR` |

Se `DATABASE_URL` ou `SECRET_KEY` não estiverem definidas, a aplicação falha
imediatamente ao subir com uma mensagem clara de qual variável falta — isso é
proposital (ver comentário em `app/config.py`).

## Autenticação

Todas as rotas exigem login, exceto `/login` e `/healthz` (e os arquivos
estáticos em `/static/`) — aplicado por um middleware em `app/main.py`
(`exigir_login`) que checa a sessão em toda requisição e redireciona pra
`/login` se não houver usuário logado.

**Não existe cadastro público de propósito** — são só duas ou três pessoas
usando o sistema (o desenvolvedor e o dono da padaria), então uma tela de
cadastro seria over-engineering. Contas são criadas rodando, localmente:
```
python scripts/criar_usuario.py
```
O script pede usuário, nome de exibição e senha (via `getpass`, não aparece
na tela) e cria ou atualiza a senha de um usuário existente com esse login.

Senha é guardada com hash `bcrypt` (nunca em texto puro). Sessão é um cookie
assinado (`itsdangerous`, via `SessionMiddleware` do Starlette) — não fica
nada de sessão guardado no banco, é tudo no próprio cookie, assinado com a
`SECRET_KEY`.

## Banco de dados: entidades e relacionamentos

6 tabelas, criadas via Alembic (não editar o schema direto no banco — sempre
via migration). Schema completo comentado em `CLAUDE.md` seção 6; resumo:

- **`funcionarios`** — nome, `ativo` (soft delete: nunca é apagado de
  verdade, só marcado inativo, pra não quebrar o histórico de pagamentos).
- **`formas_pagamento`** — tabela de apoio (hoje: Dinheiro, Pix). É tabela e
  não um valor fixo no código porque a lista deve crescer quando Vendas for
  implementado.
- **`pagamentos`** — pagamento a um funcionário. `funcionario_id` → FK pra
  `funcionarios`, `forma_pagamento_id` → FK pra `formas_pagamento`. Valor
  sempre `> 0` (constraint no banco).
- **`despesas`** — gasto da padaria (compras, fornecedores). Independente,
  sem FK pra outras tabelas do domínio. `fornecedor` é texto livre
  (proposital — só vira tabela própria se/quando fizer sentido).
- **`fechamentos_caixa`** — dois por dia (`turno`: `Manhã` ou `Noite`,
  `CHECK` constraint; `UNIQUE(data, turno)` — um fechamento por turno
  por dia, não um por dia). `total` não é uma coluna: é sempre
  `cedulas_troco + cedulas_inteiro`, calculado na hora (nunca
  armazenado, pra não correr risco de ficar desatualizado).
- **`usuarios`** — login do sistema. `username` único, `senha_hash`
  (bcrypt), `ativo` (soft delete, mesmo padrão de funcionário). Sem
  cadastro público — ver seção "Autenticação" acima.

**Relacionamento:** Funcionário 1–N Pagamento. Despesa e FechamentoCaixa são
independentes.

Todo valor monetário é `NUMERIC(10,2)`, nunca `FLOAT` (evita erro de
arredondamento com dinheiro).

## APIs e principais endpoints

Não é uma API JSON — as rotas devolvem HTML renderizado (exceto `/healthz`).
Endpoints implementados até agora:

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/login` | Formulário de login (pública) |
| `POST` | `/login` | Autentica e cria a sessão (pública) |
| `POST` | `/logout` | Encerra a sessão |
| `GET` | `/` | Dashboard: fundo de caixa (último fechamento) + saídas de hoje por forma de pagamento |
| `GET` | `/healthz` | Health check simples, `{"status": "ok"}` (pública) |
| `GET` | `/funcionarios` | Lista funcionários (só ativos por padrão; `?mostrar_inativos=true` mostra todos) |
| `GET` | `/funcionarios/novo` | Formulário de cadastro |
| `POST` | `/funcionarios` | Cria funcionário |
| `GET` | `/funcionarios/{id}/editar` | Formulário de edição |
| `POST` | `/funcionarios/{id}/editar` | Salva edição |
| `POST` | `/funcionarios/{id}/inativar` | Soft delete |
| `POST` | `/funcionarios/{id}/ativar` | Reativa |
| `GET` | `/pagamentos` | Histórico de pagamentos — só hoje por padrão; `?mostrar_todos=true`, `?funcionario_id=` ou `?data_inicio=&data_fim=` mostram outros períodos |
| `GET` | `/pagamentos/novo` | Formulário de novo pagamento |
| `POST` | `/pagamentos` | Registra pagamento |
| `GET` | `/pagamentos/{id}/editar` | Formulário de edição |
| `POST` | `/pagamentos/{id}/editar` | Salva edição |
| `GET` | `/despesas` | Histórico de despesas — só hoje por padrão; `?mostrar_todos=true` ou `?data_inicio=&data_fim=` mostram outros períodos |
| `GET` | `/despesas/novo` | Formulário de nova despesa |
| `POST` | `/despesas` | Registra despesa |
| `GET` | `/despesas/{id}/editar` | Formulário de edição |
| `POST` | `/despesas/{id}/editar` | Salva edição |
| `GET` | `/fechamentos-caixa` | Lista de fechamentos de caixa anteriores |
| `GET` | `/fechamentos-caixa/novo` | Formulário de novo fechamento |
| `POST` | `/fechamentos-caixa` | Registra fechamento (erro amigável se já existir um pro mesmo dia + turno) |
| `GET` | `/fechamentos-caixa/{id}/editar` | Formulário de edição |
| `POST` | `/fechamentos-caixa/{id}/editar` | Salva edição |

Todas as fases do MVP original estão implementadas (ver `CLAUDE.md`
seção 8).

## Regras de negócio importantes

- **Soft delete em funcionário:** nunca é feito `DELETE`. Inativar marca
  `ativo=False`, preservando o histórico de pagamentos.
- **Pagamento a ex-funcionário continua consultável:** o filtro de
  funcionário no histórico de pagamentos mostra inativos também (marcados
  como "(inativo)"), mas o formulário de **novo** pagamento só lista ativos.
- **Só Dinheiro afeta o caixa físico.** Pagamentos e despesas em Pix são
  saída real de dinheiro da padaria, mas não mexem no saldo físico do
  caixa — por isso o dashboard separa "Saídas em Dinheiro" do total geral.
- **O caixa sempre abre com o troco que sobrou do fechamento anterior**
  (confirmado com o dono da padaria — não existe um fundo fixo definido à
  parte). O dashboard usa `cedulas_troco` do fechamento mais recente
  (`FechamentoCaixa`) como "Fundo de caixa".
- **Fechamento de caixa é feito 2x por dia** (manhã e noite) — não uma
  vez, como o MVP original supôs. O desempate de "fechamento mais
  recente" no dashboard usa o turno em si (Noite > Manhã via `CASE` no
  SQL), não a ordem de inserção — importante pra não quebrar se um dia
  for lançado fora de ordem.
- **Não existe "saldo estimado do caixa" no dashboard** — chegou a ser
  implementado, mas removido: sem registro de vendas, "fundo menos
  saídas" só cresce negativo ao longo do dia, já que nunca soma o
  dinheiro que entra. Métrica reintroduzível só se/quando o sistema
  passar a registrar vendas.
- **Categoria de despesa é sempre opcional**, nunca obrigatória — o pai não
  categoriza gastos mentalmente, só anota "nome + valor".
- **Import de modelos sempre via pacote:** `from app.models import X`,
  nunca `from app.models.NOME import X` direto. Os relacionamentos entre
  tabelas são resolvidos pelo SQLAlchemy por nome de classe (string), e
  todos os 5 modelos precisam estar registrados antes da primeira query.

## Fluxos importantes

**Cadastrar e pagar um funcionário (fluxo típico):**
1. `/funcionarios/novo` → cadastra o nome.
2. `/pagamentos/novo` → o funcionário recém-criado aparece no select
   (só funcionários ativos aparecem aqui).
3. Escolhe forma de pagamento, valor, data, observação opcional → salva.
4. O pagamento aparece em `/pagamentos`, filtrável por funcionário/período.

**Validação de formulário:** os campos que o usuário digita livremente
(nome, valor, data) são recebidos como texto puro nas rotas e validados
manualmente, devolvendo a mesma tela com uma mensagem de erro em português
— em vez de deixar o FastAPI gerar um erro de validação em JSON (ruim pra
quem não é técnico). Ver `app/routers/pagamentos.py` função `criar` como
exemplo desse padrão.

**Erro inesperado (bug, banco fora do ar, etc.):** um handler global em
`app/main.py` captura qualquer exceção não tratada, grava o traceback
completo no log, e devolve uma página de erro genérica pro usuário — sem
vazar detalhes internos (stack trace, string de conexão) na tela. Ver seção
"Logs" abaixo.

## Logs

Sistema de logging usa só a biblioteca padrão do Python (`logging`), sem
dependência nova — configurado em `app/logging_config.py`.

**Onde encontrar:**
- **Console** — enquanto `uvicorn --reload` está rodando, aparece direto no
  terminal.
- **Arquivo** — `logs/app.log` (pasta criada automaticamente, git-ignorada).
  Rotaciona em 5MB, mantém os 3 arquivos anteriores (`app.log.1`,
  `app.log.2`, `app.log.3`), pra não crescer sem limite.

**Formato de cada linha:**
```
2026-08-14 13:46:18 | INFO     | app.routers.pagamentos | Pagamento registrado: id=2 funcionario_id=8 forma_pagamento_id=1 valor=99.90 data=2026-08-14
```
`data/hora | NÍVEL | módulo de origem | mensagem`. O "módulo de origem"
identifica de qual arquivo veio o log (ex: `app.routers.funcionarios`),
então dá pra saber a origem sem abrir todo o log.

**Níveis usados:**
- `INFO` — eventos de negócio que aconteceram de verdade: funcionário
  cadastrado/editado/inativado/reativado, pagamento registrado. Nível
  padrão (`LOG_LEVEL=INFO` no `.env`).
- `WARNING` — algo fora do fluxo normal, mas não é bug: tentativa de
  editar/inativar um funcionário que não existe (ex: link antigo, ID
  digitado errado na URL), tentativa de registrar pagamento pra
  funcionário ou forma de pagamento inexistente.
- `ERROR` — exceção não tratada (bug real ou infraestrutura fora do ar,
  ex: banco de dados inacessível). Sempre com o traceback completo, gerado
  automaticamente pelo handler global de erro em `app/main.py`.

**O que propositalmente não é logado:** erro de validação de formulário
(nome em branco, valor inválido, data mal formatada) — são enganos comuns
de digitação, já mostrados na tela pro usuário na hora, e logar cada um
poluiria o log sem agregar valor pra investigar um problema real. Também
nunca se loga senha, `SECRET_KEY`, ou o conteúdo de `DATABASE_URL`.

**Ajustar o nível de detalhe:** mudar `LOG_LEVEL` no `.env` (`DEBUG` mostra
mais, `WARNING` mostra menos) e reiniciar a aplicação.

### Solucionando problemas comuns

**"Erro interno" na tela (página genérica de erro):**
Olhe a linha mais recente de nível `ERROR` em `logs/app.log` — vai ter o
traceback completo apontando o arquivo e linha exatos. As causas mais
comuns até agora:
- Postgres não está rodando → `docker compose up -d` e espere alguns
  segundos antes de tentar de novo.
- Migration não aplicada → `alembic upgrade head`.

**Aplicação não sobe, erro de variável de ambiente faltando:**
`.env` não existe ou está sem `DATABASE_URL`/`SECRET_KEY`. Copie de
`.env.example`.

**`pip install` falha ao compilar algum pacote (erro sobre "Microsoft
Visual C++ Build Tools"):**
Sintoma já visto com `psycopg2-binary` no Python 3.14 — resolvido trocando
pra `psycopg[binary]`, que já está no `requirements.txt` atual. Se
acontecer com outro pacote no futuro, geralmente significa que não existe
wheel pré-compilado pra essa versão do Python/SO, e a solução é achar uma
alternativa com wheel pronto, não instalar as Build Tools (pesado e
desnecessário na maioria dos casos).

**Acentos aparecem corrompidos no console** (tipo `Aplica��o` em vez de
`Aplicação`): já corrigido em `app/logging_config.py` (o console do Windows
não usa UTF-8 por padrão). Se voltar a acontecer em outro ambiente, o
arquivo `logs/app.log` sempre está correto em UTF-8 mesmo que o console não
esteja — pode conferir por ali.

**Docker Desktop não inicia / "Virtualization support not detected":**
Verifique se o WSL2 está instalado (`wsl --status` num terminal
administrador; se não reconhecer, rode `wsl --install` como administrador e
reinicie o Windows).

**Esqueceu a senha de login:** não tem "esqueci minha senha" (não faz
sentido pra 2-3 usuários) — rode `python scripts/criar_usuario.py` de novo
com o mesmo nome de usuário; o script atualiza a senha de quem já existe.

**Ficou preso num loop de redirecionamento pra `/login`:** confirme que
existe pelo menos um usuário na tabela `usuarios` (`SELECT * FROM
usuarios;` no banco) — sem nenhum usuário cadastrado, não tem como logar
de jeito nenhum. Rode o script de criação.
