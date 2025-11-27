# Guia de Integração com Frontend (Vercel)

Este guia fornece instruções para integrar o seu frontend (Vercel) com o backend do ORKIO v4.5 (Render).

## 1. Obtenha a URL do Backend

Após o deploy no Render, você terá uma URL para o seu backend, por exemplo:

`https://orkio-backend-v4-5-clean.onrender.com`

## 2. Configure a Variável de Ambiente no Vercel

1. Vá para o seu projeto no Vercel
2. Clique em **"Settings"** > **"Environment Variables"**
3. Adicione a seguinte variável:

| Nome | Valor |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | A URL do seu backend no Render |

## 3. Faça um Novo Deploy no Vercel

Após adicionar a variável de ambiente, faça um novo deploy do seu frontend no Vercel para que as alterações entrem em vigor.

## 4. Valide a Integração

Abra o seu frontend e verifique se ele está se comunicando corretamente com o backend. Você pode testar:

- Login de usuário
- Criação de agente
- Upload de documento
- Resposta do RAG
