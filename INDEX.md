# ORKIO V4 - ÍNDICE DO PACOTE PARA DEV

## 📦 CONTEÚDO DESTE PACOTE

### 📄 Documentação Principal

1. **README_DEV.md** - Resumo completo do problema e contexto
2. **CREDENTIALS_AND_URLS.md** - Todas as credenciais, URLs e variáveis de ambiente
3. **deploy_logs_latest.txt** - Logs completos do último deploy falhado
4. **INDEX.md** - Este arquivo (índice do pacote)

---

### 🔧 Arquivos de Configuração

#### Docker & Deploy
- `Dockerfile` - Configuração do container Docker
- `start.sh` - Script de startup (roda migrações + inicia servidor)
- `Procfile` - Configuração do Render (não usado, Docker tem prioridade)
- `runtime.txt` - Versão do Python (3.11.0)

#### Banco de Dados & Migrações
- `alembic.ini` - Configuração do Alembic
- `migrations/env.py` - Configuração do Alembic para usar DATABASE_URL da env
- `migrations/versions/` - Todas as migrações do banco (9 arquivos)

#### Dependências
- `requirements.txt` - Todas as dependências Python (incluindo psycopg e psycopg2-binary)

---

### 💻 Código do Backend

#### Estrutura Principal
```
app/
├── main.py (antigo, não usado)
├── main_v4.py (ATUAL - ponto de entrada do FastAPI)
├── core/
│   ├── config.py (configurações gerais)
│   ├── database.py (SQLAlchemy engine - ANTIGO)
│   ├── security.py (autenticação JWT, get_current_user)
│   ├── auth_v4.py (autenticação v4)
│   └── encryption.py (criptografia)
├── db/
│   └── database.py (SQLAlchemy engine - ATUAL, pool ultra-conservador)
├── models/
│   └── models.py (todos os modelos SQLAlchemy)
├── api/
│   ├── v4/ (rotas v4 - ATUAL)
│   │   ├── auth/ (login, registro)
│   │   ├── user/ (rotas do usuário)
│   │   │   ├── apps.py
│   │   │   ├── usage.py
│   │   │   ├── playground.py
│   │   │   └── ...
│   │   └── ...
│   └── admin_v4/ (rotas admin v4)
├── services/
│   ├── llm.py (integração com LLMs)
│   ├── llm_manager.py (gerenciador de LLMs)
│   ├── rag.py (RAG service)
│   ├── rag_service.py (RAG service v2)
│   ├── vectorize.py (vetorização)
│   ├── document_processor.py (processamento de documentos)
│   ├── orchestrator.py (orquestração)
│   └── ...
└── rag/
    ├── models.py (modelos RAG)
    ├── events.py (eventos RAG)
    ├── embeddings.py (embeddings)
    ├── monitor.py (monitoramento)
    └── utils/ (parsers, OCR, audio)
```

---

### 🔍 ARQUIVOS CRÍTICOS PARA REVISÃO

#### 1. Configuração do Banco de Dados
- ✅ **`app/db/database.py`** - Pool de conexões (ATUAL)
  - Configurado com `pool_size=1, max_overflow=0`
  - Usa `pool_pre_ping=True` e `pool_recycle=300`
  
- ⚠️ **`app/core/database.py`** - Engine antigo (NÃO USADO?)
  - Pode estar causando conflito

#### 2. Migrações do Alembic
- ✅ **`migrations/env.py`** - Configurado para usar DATABASE_URL da env
  - Tem prints de debug para verificar DATABASE_URL
  
- ✅ **`alembic.ini`** - Configuração do Alembic
  - URL hardcoded: `postgresql+psycopg://orkio:orkio@localhost:5432/orkio`
  - Mas env.py sobrescreve com DATABASE_URL da env

#### 3. Startup & Deploy
- ✅ **`start.sh`** - Script de startup
  - Verifica se DATABASE_URL está definida
  - Roda `alembic upgrade head`
  - Inicia `uvicorn app.main:app`
  - **PROBLEMA:** Está usando `app.main:app` mas o correto é `app.main_v4:app`?

- ✅ **`Dockerfile`** - Configuração do Docker
  - CMD: `["sh", "start.sh"]`

#### 4. Dependências
- ✅ **`requirements.txt`**
  - `psycopg[binary]==3.2.1` (psycopg3)
  - `psycopg2-binary==2.9.9` (psycopg2)
  - **PROBLEMA:** Ambos instalados, SQLAlchemy usa psycopg2 por padrão

---

### 🐛 PROBLEMAS IDENTIFICADOS

#### 1. Erro de Autenticação PostgreSQL
```
FATAL: password authentication failed for user "postgres"
```
- DATABASE_URL usa `postgres.sqiiakwpsinglcvujqyj` mas erro mostra `postgres`
- Possível problema no parsing da URL pelo psycopg2

#### 2. Conflito psycopg2 vs psycopg3
- Ambos instalados no requirements.txt
- SQLAlchemy usa psycopg2 por padrão quando URL é `postgresql://`
- Para forçar psycopg3, URL deveria ser `postgresql+psycopg://`

#### 3. Startup Script
- `start.sh` usa `app.main:app` mas o arquivo correto pode ser `app.main_v4:app`
- Verificar qual é o ponto de entrada correto

#### 4. Pool de Conexões
- Configurado ultra-conservador (`pool_size=1, max_overflow=0`)
- Pode estar causando problemas com Supabase Session Pooler

---

### 📋 CHECKLIST PARA O DEV

#### Verificações Iniciais
- [ ] Confirmar senha do Supabase está correta
- [ ] Testar conexão manual com psql
- [ ] Verificar formato do usuário no Session Pooler

#### Correções de Código
- [ ] Decidir: usar psycopg2 OU psycopg3 (remover um deles)
- [ ] Corrigir DATABASE_URL format (postgresql:// vs postgresql+psycopg://)
- [ ] Verificar ponto de entrada correto (app.main vs app.main_v4)
- [ ] Revisar configuração do pool em database.py
- [ ] Verificar se há dois arquivos database.py (core/ e db/)

#### Testes
- [ ] Testar conexão local com DATABASE_URL do Supabase
- [ ] Rodar migrações localmente
- [ ] Testar startup do servidor localmente
- [ ] Deploy de teste no Render

---

### 🚀 PRÓXIMOS PASSOS RECOMENDADOS

1. **Verificar senha do Supabase**
   - Resetar senha se necessário
   - Testar conexão manual com psql

2. **Simplificar drivers PostgreSQL**
   - Remover psycopg2-binary OU psycopg[binary]
   - Ajustar DATABASE_URL de acordo

3. **Corrigir start.sh**
   - Verificar ponto de entrada correto
   - Adicionar mais logs de debug

4. **Testar localmente**
   - Usar Docker para simular ambiente do Render
   - Verificar se migrações rodam corretamente

5. **Deploy incremental**
   - Fazer deploy com correções mínimas
   - Verificar logs detalhadamente

---

### 📞 SUPORTE

Se precisar de mais informações ou logs adicionais, entre em contato:

**Cliente:** Daniel Graebin (dangraebin@gmail.com)  
**Desenvolvedor:** PATROAI Dev  
**Projeto:** Orkio v4  
**Data:** 26 de Novembro de 2025

---

**FIM DO ÍNDICE**

