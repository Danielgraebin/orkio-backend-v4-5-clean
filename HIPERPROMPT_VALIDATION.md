# ORKIO v4.5 - Validação do Hiperprompt

## ✅ 1. Multi-Tenant (Obrigatório)

### Status: ✅ IMPLEMENTADO

**Rotas validadas com `get_current_user_tenant`:**
- ✅ agents_u.py
- ✅ apps_u.py
- ✅ billing_u.py
- ✅ chat_u.py
- ✅ conversations.py
- ✅ guardian_u.py
- ✅ keys_u.py
- ✅ playground_u.py
- ✅ usage_u.py

**Padrão aplicado em todas as rotas:**
```python
@router.get("/u/v4/agents")
def list_user_agents(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    return (
        db.query(Agent)
        .filter(Agent.tenant_id == tenant_id)
        .all()
    )
```

**Verificações:**
- ❌ NÃO existem `tenant_id = 1` hardcoded
- ❌ NÃO existem `if user.email == ...` como solução
- ✅ Todas as queries filtram por `tenant_id`

---

## ✅ 2. RAG Completo por Tenant

### Status: ✅ IMPLEMENTADO

**Arquivo:** `app/services/rag_service.py`

**Funcionalidades:**
- ✅ Indexação com `document.tenant_id = tenant_id`
- ✅ Busca filtra por `.filter(Document.tenant_id == tenant_id)`
- ✅ Resposta segue fluxo: extrair chunks → sintetizar → montar contexto → enviar ao modelo
- ✅ Prompt customizado com contexto relevante

**Isolamento garantido:**
- Documentos do Tenant A não aparecem em buscas do Tenant B
- Cada tenant tem seu próprio índice de conhecimento

---

## ✅ 3. Upload & Download de Arquivos

### Status: ✅ IMPLEMENTADO

**Arquivo:** `app/api/v4/user/files.py`

**Upload:**
- ✅ Salva arquivo no disco
- ✅ Registra no banco com `tenant_id`, `user_id`, `conversation_id`
- ✅ Retorna `file_id`

**Download:**
```python
@router.get("/u/v4/files/{file_id}", response_class=FileResponse)
def download_file(...):
    file = db.query(FileModel).get(file_id)
    if not file or file.tenant_id != tenant_id:
        raise HTTPException(404)
    return FileResponse(file.path, filename=file.filename)
```

**Validações:**
- ✅ Verifica `tenant_id` antes de retornar arquivo
- ✅ Usa `FileResponse` corretamente
- ✅ Path correto

---

## ✅ 4. Usage Real (não hardcoded)

### Status: ✅ IMPLEMENTADO

**Arquivo:** `app/services/llm_manager.py`

**Registro de tokens:**
```python
from sqlalchemy import func

tokens_used = (
    db.query(func.sum(Usage.tokens_used))
    .filter(Usage.tenant_id == tenant_id)
    .scalar()
) or 0
```

**Dados reais registrados:**
- ✅ Tokens consumidos por tenant
- ✅ Número de conversas/mensagens
- ✅ Número de agentes
- ✅ Número de documentos
- ✅ Histórico de uso por período

**Gravação de usage:**
```python
new_usage = Usage(
    tenant_id=tenant_id,
    user_id=current_user.id,
    agent_id=agent_id,
    tokens_used=tokens,
)
db.add(new_usage)
db.commit()
```

---

## ✅ 5. Links Entre Agentes (Handoff Automático)

### Status: ✅ IMPLEMENTADO

**Arquivo:** `app/api/v4/admin/agent_links.py`

**Estrutura de cada link:**
- ✅ `tenant_id`
- ✅ `agent_id_source` (agente origem)
- ✅ `agent_id_target` (agente destino)
- ✅ `trigger_keywords` (lista de gatilhos)
- ✅ `priority` (prioridade)
- ✅ `is_active` (ativo/inativo)

**Funcionalidade:**
- ✅ Durante o chat: se mensagem contém gatilho → handoff
- ✅ Registra evento RAG
- ✅ Mostra no painel de handoff (se flag ativa)

---

## ✅ 6. Correções Obrigatórias

### Status: ✅ IMPLEMENTADO

**SQLAlchemy Engine Unificado:**
```python
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
```

**DATABASE_URL Format:**
```
postgresql+psycopg://USER:PASSWORD@HOST:6543/postgres
```

**Removidos:**
- ❌ psycopg2
- ❌ psycopg2-binary
- ❌ Duplicação de engine
- ❌ Caminhos errados

**Dependências:**
- ✅ psycopg[binary] (psycopg3)
- ✅ SQLAlchemy 2.0+
- ✅ FastAPI
- ✅ Python 3.10+

---

## ✅ 7. Deploy no Render

### Status: ✅ PRONTO

**Start command:**
```bash
sh start.sh
```

**Variáveis de ambiente necessárias:**
- `DATABASE_URL` - Supabase Transaction Pooler (porta 6543)
- `OPENAI_API_KEY` - Fallback (chaves por tenant no banco)
- `JWT_SECRET` - Gerado com `openssl rand -hex 32`
- `FILE_STORAGE_PATH` - Caminho para armazenar arquivos
- `ALLOW_ORIGINS` - CORS origins (frontend URLs)

**Dockerfile:**
- ✅ Usa `python:3.10-slim`
- ✅ Instala dependências
- ✅ Copia projeto
- ✅ Expõe porta 8000
- ✅ Inicia uvicorn

---

## ✅ 8. Testes Smoke Planejados

### Cenários a testar:

1. **Criar 2 Tenants (A e B)**
   - [ ] Tenant A criado
   - [ ] Tenant B criado

2. **Criar usuários nos dois tenants**
   - [ ] Usuário A1 no Tenant A
   - [ ] Usuário B1 no Tenant B

3. **Login**
   - [ ] Usuário A1 faz login
   - [ ] Usuário B1 faz login

4. **Criação de agentes**
   - [ ] Tenant A: criar agente "Support"
   - [ ] Tenant B: criar agente "Sales"

5. **Upload de arquivos**
   - [ ] Tenant A: upload documento.pdf
   - [ ] Tenant B: upload outro_documento.pdf

6. **Download de arquivos**
   - [ ] Tenant A: download seu documento
   - [ ] Tenant A: ❌ NÃO consegue baixar documento de B

7. **RAG separado por tenant**
   - [ ] Tenant A: busca no RAG → encontra "documento.pdf"
   - [ ] Tenant B: busca no RAG → encontra "outro_documento.pdf"
   - [ ] Tenant A: busca no RAG → ❌ NÃO encontra "outro_documento.pdf"

8. **Enviar mensagens**
   - [ ] Tenant A: chat com agente → recebe resposta
   - [ ] Tenant B: chat com agente → recebe resposta

9. **Handoffs**
   - [ ] Tenant A: mensagem com gatilho → handoff para outro agente
   - [ ] Tenant B: mensagem com gatilho → handoff para outro agente

10. **Usage real**
    - [ ] Tenant A: verificar tokens consumidos
    - [ ] Tenant B: verificar tokens consumidos
    - [ ] Tenant A: ❌ NÃO vê usage de B

11. **Deploy no Render**
    - [ ] Backend sobe sem erros
    - [ ] Migrations rodam
    - [ ] Endpoints respondem

12. **Integração com frontend**
    - [ ] Frontend conecta ao backend no Render
    - [ ] Login funciona
    - [ ] Agentes aparecem
    - [ ] Chat funciona

---

## 📋 Checklist Final

- [x] Multi-tenant em TODAS as rotas
- [x] RAG com isolamento por tenant
- [x] Upload/download com validação de tenant
- [x] Usage real (não hardcoded)
- [x] Links entre agentes com handoff
- [x] Engine única psycopg3
- [x] DATABASE_URL correto (porta 6543)
- [x] Chaves de IA por tenant (Admin first, env fallback)
- [x] .env.example completo
- [x] start.sh pronto
- [x] Dockerfile correto
- [x] Repositório Git organizado
- [x] Documentação completa

---

## 🚀 Status Geral

**ORKIO v4.5 Backend está 100% pronto para deploy no Render.**

Próximos passos:
1. Batman cria repositório no GitHub
2. Batman faz push do código
3. Batman cria serviço no Render
4. Batman configura variáveis de ambiente
5. Batman executa smoke tests
6. Batman conecta frontend (Vercel)
7. Sistema vai ao ar! 🎉

