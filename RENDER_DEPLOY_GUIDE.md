# Guia de Deploy no Render (Passo-a-Passo)

Este guia fornece instruções passo-a-passo para fazer o deploy do ORKIO v4.5 Backend no Render.

## 1. Crie um Novo Web Service

1. Vá para https://dashboard.render.com
2. Clique em **"New"** > **"Web Service"**
3. Selecione **"Git Provider"** > **"GitHub"**
4. Selecione o repositório `orkio-backend-v4-5-clean`

## 2. Configure o Serviço

O Render vai detectar automaticamente o `render.yaml` e pré-configurar tudo. Você só precisa revisar e confirmar:

- **Name**: `orkio-backend-v4-5-clean`
- **Branch**: `main`
- **Build Command**: `pip install -r requirements.txt && alembic upgrade head`
- **Start Command**: `sh start.sh`

## 3. Adicione as Variáveis de Ambiente

Na seção **"Environment"**, adicione as seguintes variáveis:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | Sua string de conexão do Supabase |
| `JWT_SECRET` | `8f2df1ee4b6a9b7e9a1fd8c7a09efbdc4a0d62bbf76719a473a96ef2c45d9e52` |
| `OPENAI_API_KEY` | Sua chave de API da OpenAI |
| `ENVIRONMENT` | `production` |

## 4. Faça o Deploy

Clique em **"Create Web Service"** e aguarde o deploy ser concluído (pode levar de 5 a 10 minutos).

## 5. Valide o Deploy

Quando o deploy terminar, copie a URL do seu backend (ex: `https://orkio-backend-v4-5-clean.onrender.com`) e teste no navegador:

`https://orkio-backend-v4-5-clean.onrender.com/docs`
