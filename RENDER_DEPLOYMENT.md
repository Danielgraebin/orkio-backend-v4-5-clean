# ORKIO v4.5 Backend - Guia de Deploy no Render

## 📋 Variáveis de Ambiente Necessárias

Adicione as seguintes variáveis de ambiente no painel do Render:

### 1. **Banco de Dados (Supabase)**
```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:6543/postgres
```
**Formato esperado:** `postgresql+psycopg://` (psycopg3, SEM psycopg2)
**Porta:** 6543 (Transaction Pooler do Supabase)

### 2. **Autenticação JWT**
```
JWT_SECRET=sua_chave_secreta_super_segura_aqui_com_minimo_32_caracteres
```
**Recomendação:** Gere uma chave forte com `openssl rand -hex 32`

### 3. **OpenAI / LLM**
```
OPENAI_API_KEY=sk-...seu_token_aqui
OPENAI_MODEL_DEFAULT=gpt-4.1-mini
OPENAI_ALLOWED_MODELS=gpt-4o-mini,gpt-4.1,gpt-4.1-mini,gpt-4.1-nano,gpt-5
```

### 4. **Configurações Opcionais**
```
ORKIO_LLM_TIMEOUT=60
ORKIO_LLM_RETRIES=2
LOG_LEVEL=INFO
```

## 🚀 Passos para Deploy

### 1. Criar Serviço no Render
- Acesse [render.com](https://render.com)
- Clique em **"New +"** → **"Web Service"**
- Conecte seu repositório Git (GitHub/GitLab)
- Selecione a branch `main` ou `master`

### 2. Configurar Serviço
- **Name:** `orkio-backend-v4-5`
- **Environment:** Python 3.11
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `sh start.sh`
- **Region:** Selecione a mais próxima (ex: São Paulo)
- **Plan:** Starter (ou superior conforme necessário)

### 3. Adicionar Variáveis de Ambiente
No painel do Render, vá para **"Environment"** e adicione todas as variáveis listadas acima.

### 4. Deploy
Clique em **"Create Web Service"**. O Render iniciará o build automaticamente.

## ✅ Verificar Deploy

Após o deploy, acesse:
```
https://orkio-backend-v4-5.onrender.com/docs
```

Você deve ver a documentação interativa do Swagger com todos os endpoints.

## 🔍 Troubleshooting

### Erro: `DATABASE_URL` não configurada
- Verifique se a variável foi adicionada corretamente no painel do Render
- Certifique-se de usar o formato `postgresql+psycopg://...`

### Erro: Migrations falhando
- O `start.sh` executa `alembic upgrade head` automaticamente
- Se houver erro, verifique se o banco de dados está acessível

### Erro: OpenAI API key inválida
- Verifique se a chave foi copiada corretamente (sem espaços extras)
- Certifique-se de que a chave tem permissão para o modelo especificado

## 📊 Monitoramento

No painel do Render, você pode:
- Ver logs em tempo real (**"Logs"**)
- Monitorar uso de CPU/Memória (**"Metrics"**)
- Configurar alertas de erro

## 🔄 Atualizações

Para fazer deploy de novas versões:
1. Faça commit e push para a branch principal
2. O Render detectará a mudança e iniciará o build automaticamente
3. Monitore o progresso na aba **"Deployments"**

## 📞 Suporte

Em caso de problemas, consulte:
- [Documentação do Render](https://render.com/docs)
- [Logs do Render](https://dashboard.render.com)
- Arquivo `README_DEPLOY.md` no repositório
