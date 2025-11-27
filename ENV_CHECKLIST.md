# Checklist de Variáveis de Ambiente e Configurações

Este documento lista todas as variáveis de ambiente necessárias para configurar o ORKIO v4.5 Backend.

## Variáveis Obrigatórias

| Variável | Descrição | Exemplo |
|---|---|---|
| `DATABASE_URL` | String de conexão com o banco de dados Supabase (Transaction Pooler) | `postgresql+psycopg://postgres:<sua-senha>@db.sqiiakwpsinglcvujqyj.supabase.co:6543/postgres` |
| `JWT_SECRET` | Chave secreta para assinar os tokens JWT | `8f2df1ee4b6a9b7e9a1fd8c7a09efbdc4a0d62bbf76719a473a96ef2c45d9e52` |

## Variáveis Opcionais (com Fallback)

| Variável | Descrição | Exemplo |
|---|---|---|
| `OPENAI_API_KEY` | Chave de API da OpenAI (usada como fallback se não configurada no Admin) | `sk-...` |
| `OPENAI_MODEL_DEFAULT` | Modelo padrão da OpenAI | `gpt-4.1-mini` |
| `ALLOWED_MODELS` | Lista de modelos permitidos | `["gpt-4.1-mini","gpt-4.1-nano","gemini-2.5-flash"]` |
| `FILE_STORAGE_PATH` | Caminho para armazenar arquivos de upload | `/tmp/orkio-files` |
| `ALLOW_ORIGINS` | Lista de origens permitidas para CORS | `["http://localhost:3000","https://seu-frontend.vercel.app"]` |
| `ENVIRONMENT` | Ambiente de execução (development ou production) | `production` |
