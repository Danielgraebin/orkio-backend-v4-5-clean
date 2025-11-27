# ORKIO V4 - CREDENCIAIS E URLs

## 🌐 URLs DO PROJETO

### Backend (Render)
```
URL: https://orkio-backend.onrender.com
Status: Deploy falhando (erro de autenticação PostgreSQL)
Repositório: https://github.com/Danielgraebin/Orkio-v4
Branch: main
Último commit: da69c9b (fix: adiciona psycopg2-binary de volta)
```

### Frontend User (Vercel)
```
URL: https://orkio-v4.vercel.app
Status: Funcionando (mas com erro 401 ao chamar backend)
Repositório: https://github.com/Danielgraebin/Orkio-v4
Branch: main
```

### Frontend Admin (Vercel)
```
URL: (ainda não configurado)
Status: Pendente
```

---

## 🔐 VARIÁVEIS DE AMBIENTE (RENDER)

### DATABASE_URL
```bash
# Session Pooler IPv4 compatible (porta 5432)
DATABASE_URL=postgresql://postgres.sqiiakwpsinglcvujqyj:HgXu3LbDdU8Jvw5@aws-1-us-east-1.pooler.supabase.com:5432/postgres
```

**FORMATO:**
- Protocol: `postgresql://`
- User: `postgres.sqiiakwpsinglcvujqyj`
- Password: `HgXu3LbDdU8Jvw5`
- Host: `aws-1-us-east-1.pooler.supabase.com`
- Port: `5432` (Session Pooler)
- Database: `postgres`

**NOTA:** Este é o Session Pooler do Supabase (IPv4 compatible). Também existe:
- Direct Connection (porta 5432, IPv6): `db.sqiiakwpsinglcvujqyj.supabase.co:5432`
- Transaction Pooler (porta 6543): `aws-1-us-east-1.pooler.supabase.com:6543`

### FRONTEND_URL
```bash
FRONTEND_URL=https://orkio-v4.vercel.app
```

### OPENAI_API_KEY
```bash
OPENAI_API_KEY=sk-proj-***MASCARADO***
```

### SECRET_KEY
```bash
SECRET_KEY=***MASCARADO***
```

### WEBHOOK_SECRET
```bash
WEBHOOK_SECRET=***MASCARADO***
```

---

## 🗄️ SUPABASE

### Informações do Projeto
```
Project ID: sqiiakwpsinglcvujqyj
Project Name: orkio-v4
Region: us-east-1
Tier: Free
```

### Connection Strings

#### 1. Direct Connection (IPv6)
```
postgresql://postgres:HgXu3LbDdU8Jvw5@db.sqiiakwpsinglcvujqyj.supabase.co:5432/postgres
```
- ⚠️ **Não IPv4 compatible** (requer IPv6 ou IPv4 add-on pago)
- Usado para conexões diretas ao banco

#### 2. Session Pooler (IPv4 compatible) ✅ ATUAL
```
postgresql://postgres.sqiiakwpsinglcvujqyj:HgXu3LbDdU8Jvw5@aws-1-us-east-1.pooler.supabase.com:5432/postgres
```
- ✅ **IPv4 compatible** (grátis)
- ✅ Ideal para IPv4 networks (Render)
- ✅ Shared Pooler (grátis)
- Pool Size: 15 (configurado no Supabase)
- Max Client Connections: 200 (teórico)

#### 3. Transaction Pooler (IPv4 compatible)
```
postgresql://postgres.sqiiakwpsinglcvujqyj:HgXu3LbDdU8Jvw5@aws-1-us-east-1.pooler.supabase.com:6543/postgres
```
- ✅ **IPv4 compatible** (grátis)
- ⚠️ **NÃO suporta PREPARE statements**
- Ideal para aplicações stateless (serverless, edge functions)
- **TENTAMOS E DEU ERRO DE AUTENTICAÇÃO**

### Credenciais
```
User (Direct): postgres
User (Pooler): postgres.sqiiakwpsinglcvujqyj
Password: HgXu3LbDdU8Jvw5
Database: postgres
```

### URLs do Supabase
```
Dashboard: https://supabase.com/dashboard/project/sqiiakwpsinglcvujqyj
Database Settings: https://supabase.com/dashboard/project/sqiiakwpsinglcvujqyj/settings/database
```

---

## 🚀 RENDER

### Service Information
```
Service ID: srv-d4gct9re5dus73cotrn0
Service Name: orkio-backend
Service Type: Web Service
Region: Oregon (US West)
Instance Type: Free
```

### Dashboard URLs
```
Service: https://dashboard.render.com/web/srv-d4gct9re5dus73cotrn0
Events: https://dashboard.render.com/web/srv-d4gct9re5dus73cotrn0/events
Environment: https://dashboard.render.com/web/srv-d4gct9re5dus73cotrn0/env
Logs: https://dashboard.render.com/web/srv-d4gct9re5dus73cotrn0/logs
```

### Build & Deploy
```
Build Command: (Docker build automático)
Start Command: sh start.sh
Dockerfile: ./backend/Dockerfile
```

---

## 📧 CONTATO

```
Cliente: Daniel Graebin
Email: dangraebin@gmail.com
Desenvolvedor: PATROAI Dev
Projeto: Orkio v4
Data: 26 de Novembro de 2025
```

---

## ⚠️ NOTAS IMPORTANTES

1. **Senha do Supabase:** A senha `HgXu3LbDdU8Jvw5` está sendo usada mas o deploy falha com "password authentication failed"
2. **Formato do usuário:** O Session Pooler usa `postgres.sqiiakwpsinglcvujqyj` (não apenas `postgres`)
3. **Pool de conexões:** Configurado para `pool_size=1, max_overflow=0` (ultra-conservador para Supabase free tier)
4. **psycopg2 vs psycopg3:** Ambos estão instalados, mas SQLAlchemy está usando psycopg2
5. **Migrações:** Alembic está configurado para rodar no startup via `start.sh`

---

## 🔍 PRÓXIMOS PASSOS

1. ✅ Verificar se a senha está correta no Supabase
2. ✅ Testar conexão manual com psql ou Python
3. ✅ Confirmar o formato correto do usuário para Session Pooler
4. ✅ Decidir entre psycopg2 OU psycopg3 (não ambos)
5. ✅ Revisar configuração do pool no database.py
6. ✅ Considerar usar Direct Connection se IPv6 estiver disponível no Render

