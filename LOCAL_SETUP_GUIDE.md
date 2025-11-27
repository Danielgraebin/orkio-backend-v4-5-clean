# Guia Completo de Setup Local e Testes do ORKIO v4.5 Backend

Este guia fornece instruções passo-a-passo para configurar e testar o backend do ORKIO v4.5 em seu ambiente local.

## 1. Pré-requisitos

- Python 3.10 ou superior
- Git
- Docker (opcional, para rodar o banco de dados)

## 2. Configuração do Ambiente

### 2.1. Clone o Repositório

```bash
git clone https://github.com/Danielgraebin/orkio-backend-v4-5-clean.git
cd orkio-backend-v4-5-clean
```

### 2.2. Crie um Ambiente Virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2.3. Instale as Dependências

```bash
pip install -r requirements.txt
```

## 3. Configuração do Banco de Dados

### 3.1. Crie um Arquivo `.env`

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

### 3.2. Configure a DATABASE_URL

Abra o arquivo `.env` e configure a `DATABASE_URL` com a sua string de conexão do Supabase:

```
DATABASE_URL=postgresql+psycopg://postgres:<sua-senha>@db.sqiiakwpsinglcvujqyj.supabase.co:6543/postgres
```

## 4. Aplique as Migrações

```bash
alembic upgrade head
```

## 5. Rode o Servidor

```bash
sh start.sh
```

O servidor estará rodando em `http://localhost:8000`.

## 6. Testes

### 6.1. Acesse a Documentação da API

Abra o navegador e acesse `http://localhost:8000/docs` para ver a documentação da API e testar os endpoints.

### 6.2. Rode os Smoke Tests

Opcionalmente, você pode rodar os smoke tests para validar o fluxo completo:

```bash
python tools/smoke_tests.py
```
