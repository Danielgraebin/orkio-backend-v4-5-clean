# ORKIO v4.5 Backend - Instruções de Deploy

## 🚀 Status Atual

**Repositório local pronto para push no GitHub.**

Todas as funcionalidades implementadas conforme o hiperprompt:
- ✅ Multi-tenant em todas as rotas
- ✅ RAG com isolamento por tenant
- ✅ Upload/download com validação de tenant
- ✅ Usage real (não hardcoded)
- ✅ Links entre agentes com handoff
- ✅ Engine única psycopg3
- ✅ Chaves de IA por tenant (Admin first, env fallback)

---

## 📋 Próximos Passos para Batman

### 1. Criar Repositório no GitHub

```bash
# No GitHub (web):
1. Clique em "New Repository"
2. Nome: orkio-backend-v4-5-clean
3. Descrição: ORKIO v4.5 Backend - Multi-tenant, RAG, Deploy Ready
4. Privado (recomendado)
5. Clique em "Create repository"
```

### 2. Fazer Push do Código

```bash
# No seu terminal local:
cd /home/ubuntu/projects/orkio-backend-v4-5

# Adicionar remote
git remote add origin https://github.com/seu-usuario/orkio-backend-v4-5-clean.git

# Fazer push
git branch -M main
git push -u origin main
```

### 3. Criar Serviço no Render

```
1. Acesse render.com
2. Clique em "New +"
3. Selecione "Web Service"
4. Conecte seu repositório GitHub (orkio-backend-v4-5-clean)
5. Configure:
   - Name: orkio-backend-v4-5
   - Environment: Python 3
   - Build Command: pip install -r requirements.txt && alembic upgrade head
   - Start Command: sh start.sh
   - Plan: Free (ou pago, conforme necessário)
```

### 4. Configurar Variáveis de Ambiente no Render

No painel do Render, adicione as seguintes variáveis de ambiente:

```
DATABASE_URL=postgresql+psycopg://postgres.USER:PASSWORD@db.PROJECT.supabase.co:6543/postgres
JWT_SECRET=8f2df1ee4b6a9b7e9a1fd8c7a09efbdc4a0d62bbf76719a473a96ef2c45d9e52
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL_DEFAULT=gpt-4.1-mini
ALLOWED_MODELS=["gpt-4.1-mini","gpt-4.1-nano","gemini-2.5-flash"]
FILE_STORAGE_PATH=/tmp/orkio-files
ALLOW_ORIGINS=["http://localhost:3000","https://seu-frontend.vercel.app"]
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
```

### 5. Conectar Frontend (Vercel)

No seu projeto Next.js (Vercel), adicione a variável de ambiente:

```
NEXT_PUBLIC_API_BASE_URL=https://orkio-backend-v4-5.onrender.com
```

### 6. Executar Smoke Tests

Após o deploy estar ativo, execute os testes:

```bash
# Testar login
curl -X POST https://orkio-backend-v4-5.onrender.com/u/v4/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Testar listar agentes
curl -X GET https://orkio-backend-v4-5.onrender.com/u/v4/agents \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Testar health check
curl https://orkio-backend-v4-5.onrender.com/health
```

---

## 📁 Estrutura do Repositório

```
orkio-backend-v4-5-clean/
├── app/
│   ├── api/
│   │   ├── users/              # Rotas do User Console (multi-tenant)
│   │   ├── v4/                 # Rotas da API v4
│   │   └── admin/              # Rotas do Admin
│   ├── core/
│   │   ├── database.py         # Engine única psycopg3
│   │   ├── auth_v4.py          # Autenticação com JWT
│   │   ├── deps.py             # Dependências centralizadas
│   │   └── security.py         # Funções de segurança
│   ├── models/
│   │   └── models.py           # Modelos SQLAlchemy
│   ├── services/
│   │   ├── rag_service.py      # RAG com isolamento por tenant
│   │   ├── llm_manager.py      # Gerenciador de LLM com chaves por tenant
│   │   └── ...
│   └── main_v4.py             # Aplicação FastAPI
├── alembic/
│   ├── versions/               # Migrations (0001...0009)
│   ├── env.py                  # Configuração do Alembic
│   └── alembic.ini             # Configuração do Alembic
├── tools/
│   ├── smoke_tests.py          # Testes automatizados
│   └── ...
├── requirements.txt            # Dependências (psycopg3 only)
├── start.sh                    # Script de inicialização
├── .env.example                # Exemplo de variáveis de ambiente
├── Dockerfile                  # Para deploy em containers
├── README_DEPLOY.md            # Instruções de deploy
├── HIPERPROMPT_VALIDATION.md   # Validação do hiperprompt
└── DEPLOY_INSTRUCTIONS.md      # Este arquivo

```

---

## 🔐 Segurança

### Variáveis de Ambiente

**NUNCA** commit `.env` ou senhas no repositório.

Use `.env.example` como template e preencha localmente.

### Chaves de IA

As chaves de IA são armazenadas:
1. **Primário:** No banco de dados (tabela `llm_api_keys`) por tenant
2. **Fallback:** Variáveis de ambiente (para desenvolvimento)

O backend sempre tenta usar a chave do tenant primeiro, depois fallback para env.

### JWT Secret

Gerado com:
```bash
openssl rand -hex 32
```

Ou em Python:
```python
import secrets
secrets.token_hex(32)
```

---

## 📊 Monitoramento

### Logs no Render

Acesse os logs em tempo real:
```
Render Dashboard → Seu Serviço → Logs
```

### Health Check

```bash
curl https://orkio-backend-v4-5.onrender.com/health
```

Resposta esperada:
```json
{
  "status": "ok",
  "version": "4.5.0",
  "database": "connected"
}
```

---

## 🐛 Troubleshooting

### Erro: "DATABASE_URL not found"
- Verifique se a variável está configurada no Render
- Formato correto: `postgresql+psycopg://...`

### Erro: "psycopg2 not found"
- Verifique `requirements.txt` - deve usar `psycopg[binary]`
- NÃO deve ter `psycopg2` ou `psycopg2-binary`

### Erro: "Migration failed"
- Verifique se o banco está acessível
- Execute manualmente: `alembic upgrade head`

### Erro: "JWT token invalid"
- Verifique se `JWT_SECRET` está configurado
- Tokens expiram em 24 horas (configurável)

---

## 📞 Suporte

Se encontrar problemas:

1. Verifique os logs no Render
2. Valide as variáveis de ambiente
3. Teste localmente com `python -m uvicorn app.main_v4:app --reload`
4. Consulte `README_DEPLOY.md` para mais detalhes

---

## ✅ Checklist de Deploy

- [ ] Repositório criado no GitHub
- [ ] Código feito push para GitHub
- [ ] Serviço criado no Render
- [ ] Variáveis de ambiente configuradas
- [ ] Build passou sem erros
- [ ] Migrations rodaram com sucesso
- [ ] Health check respondendo
- [ ] Frontend conectado (NEXT_PUBLIC_API_BASE_URL)
- [ ] Smoke tests passando
- [ ] Logs monitorados

---

**Pronto para produção! 🚀**
