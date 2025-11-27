# ORKIO v4.5 - Backend Clean Build

Este pacote contém o backend do ORKIO v4.5 preparado para:

- **Supabase Free** (Transaction Pooler 6543)
- **Render Free** (backend)
- **Vercel Free** (frontends)

## Como rodar localmente (para o Manus)

### 1. Criar um arquivo `.env` na raiz

Baseado no `.env.example`, crie um arquivo `.env`:

```bash
# Database (Supabase Transaction Pooler - porta 6543)
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@aws-1-us-east-1.pooler.supabase.com:6543/postgres

# Auth / JWT
JWT_SECRET=trocar_por_um_segredo_forte_aqui

# OpenAI ou outro provider
OPENAI_API_KEY=sua_chave_openai_aqui

# Outros
ENV=production
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Rodar migrações

```bash
alembic upgrade head
```

### 4. Subir o servidor

```bash
uvicorn app.main_v4:app --reload
```

O servidor estará disponível em `http://localhost:8000`

## Deploy no Render

### Configuração de Variáveis de Ambiente

No painel do Render, configure:

```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@aws-1-us-east-1.pooler.supabase.com:6543/postgres
JWT_SECRET=seu_segredo_forte_aqui
OPENAI_API_KEY=sua_chave_openai_aqui
ENV=production
```

### Comando de Startup

```
sh start.sh
```

Este comando irá:
1. Executar as migrações do Alembic (`alembic upgrade head`)
2. Iniciar o servidor Uvicorn com a porta configurada pelo Render

## Estrutura do Projeto

```
orkio_backend_v4_5_clean/
├── alembic.ini                    # Configuração do Alembic
├── requirements.txt               # Dependências (psycopg3 only)
├── start.sh                       # Script de startup para Render
├── Dockerfile                     # Configuração Docker
├── README_DEPLOY.md              # Este arquivo
├── .env.example                  # Exemplo de variáveis de ambiente
├── runtime.txt                   # Versão Python (Render)
├── Procfile                      # Configuração Procfile (Heroku/Render)
│
├── app/
│   ├── main_v4.py               # Aplicação FastAPI principal
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py          # Engine única com psycopg3
│   │   ├── auth_v4.py
│   │   ├── encryption.py
│   │   └── security.py
│   ├── models/
│   ├── api/
│   ├── services/
│   ├── rag/
│   └── ...
│
├── alembic/
│   ├── env.py                   # Configuração Alembic (DATABASE_URL)
│   └── versions/                # Migrations
│       ├── 0001_initial_orkio_v4.py
│       ├── 0002_update_documents_schema.py
│       └── ...
│
└── tools/
    ├── create_user_for_testing.py
    ├── seed_users.py
    ├── update_password.py
    └── validate_txt_upload.py
```

## Pontos Importantes

### 1. Engine Única (psycopg3)

O arquivo `app/core/database.py` contém a engine única que deve ser usada em toda a aplicação:

```python
from app.core.database import SessionLocal, Base
```

Todos os imports de banco de dados devem usar este arquivo.

### 2. Variáveis de Ambiente

O `alembic/env.py` e `app/core/database.py` leem a variável `DATABASE_URL` do ambiente automaticamente.

### 3. Migrations

As migrations estão em `alembic/versions/` e são executadas automaticamente no startup pelo `start.sh`.

## Próximas Etapas (para o Manus)

1. ✅ Ajuste todos os imports para usar `app.core.database.SessionLocal`
2. ✅ Aplique o hiperprompt de tenants/RAG/User Console
3. ✅ Configure o Render com `DATABASE_URL` (pooler 6543) e start `sh start.sh`
4. ✅ Faça o deploy e envie as URLs de Admin e User para teste

## Suporte

Para dúvidas sobre o deploy, consulte:
- [Documentação FastAPI](https://fastapi.tiangolo.com/)
- [Documentação Alembic](https://alembic.sqlalchemy.org/)
- [Documentação Supabase](https://supabase.com/docs)
- [Documentação Render](https://render.com/docs)

---

**Versão:** ORKIO v4.5 Clean Build  
**Data:** Novembro 2025  
**Status:** Pronto para Deploy
