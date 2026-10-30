---
id: 11.08 Onboarding e Execução do Ambiente
aliases:
  - Onboarding e Setup
  - Execução do Ecossistema
tags:
  - tipo/projeto
  - projeto/app
  - devops
  - setup
  - docker
  - python
  - nextjs
  - cloudflare
status: ativo
modulo: App & Portal
sistema: Sienge ERP & Portal do Condômino
upstream:
  - "[[11.01 App - Portal do Condômino]]"
---

# 11.08 Onboarding, Setup & Execução do Ecossistema

> Guia passo a passo para inicialização do ambiente de desenvolvimento, execução do backend, frontend Next.js e túnel Cloudflare.

---

## 1. Pré-requisitos & Versão Crítica do Python

> [!WARNING]
> ### Atenção Crítica: Use Exclusivamente Python 3.12 (64-bit)
> * O backend utiliza bibliotecas compiladas em linguagem C (`asyncpg`, `greenlet`, `pydantic-core`).
> * No Windows, **o Python 3.13 não possui wheels binárias pré-compiladas estáveis** para essas bibliotecas e falha em tempo de execução com erros fatais como `ModuleNotFoundError: No module named 'greenlet._greenlet'` ou `asyncpg.protocol.protocol`.
> * **Sempre utilize Python 3.12** para criar e executar o ambiente virtual do backend.

### Softwares Necessários:
* **Python 3.12 (CPython 3.12.x 64-bit)**
* **Docker Desktop** (para o container PostgreSQL 16)
* **Node.js 20+ LTS** (para o frontend Next.js 15 em `portal_frontend/`)
* **Cloudflare Tunnel (`cloudflared`)** (para expor o portal com HTTPS público para testes mobile)

---

## 2. Passo a Passo: Configuração do Ambiente Inicial

### 1. Subir o container PostgreSQL 16:
```powershell
cd C:\Users\pedro\Desktop\Trabalho\Benedetto\BenedettoApp\portal_backend
docker compose up -d
```
*(Nota: O container `portal_condomino_db` roda mapeado na porta **`5433`** do host para evitar conflito com instalações locais padrão do PostgreSQL na porta `5432`).*

### 2. Configurar variáveis de ambiente (`.env`):
Copie o arquivo de exemplo caso ainda não o tenha feito:
```powershell
Copy-Item .env.example .env
```
* **Desenvolvimento offline (Mock):** Defina `SIENGE_USE_MOCK=true`.
* **Integração real:** Defina `SIENGE_USE_MOCK=false`, preenchendo `SIENGE_SUBDOMAIN`, `SIENGE_USERNAME` e `SIENGE_API_TOKEN`.

### 3. Criar ambiente virtual e instalar dependências:
```powershell
# Criação garantindo o binário do Python 3.12:
C:\Users\pedro\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv

# Instalação do pacote em modo editável com dependências de desenvolvimento:
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### 4. Aplicar migrações do banco de dados:
```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

---

## 3. Como Iniciar o Ecossistema Completo (3 Terminais)

Abra **3 terminais PowerShell** separados:

### 🟦 Terminal 1 — Backend FastAPI (Porta 8000)
```powershell
cd C:\Users\pedro\Desktop\Trabalho\Benedetto\BenedettoApp\portal_backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
* **API Local:** `http://127.0.0.1:8000`
* **Swagger UI Interativo:** `http://127.0.0.1:8000/docs`
* **Health Check:** `http://127.0.0.1:8000/api/v1/health`

### 🟧 Terminal 2 — Frontend Next.js 15 (Porta 3000)
```powershell
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
cd C:\Users\pedro\Desktop\Trabalho\Benedetto\BenedettoApp\portal_frontend
npm run dev
```
* **App Web:** `http://localhost:3000`
* **Proxy Transparente:** O Next.js (`next.config.ts`) reescreve automaticamente requisições para `/api/v1/:path*` e `/media/:path*` para `http://127.0.0.1:8000`.

### 🟨 Terminal 3 — Cloudflare Quick Tunnel (Acesso Público HTTPS)
```powershell
& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:3000 --no-autoupdate
```
* O túnel gerará uma URL temporária com SSL: `https://<hash>.trycloudflare.com`.
* Permite testar o PWA instantaneamente em smartphones conectados à internet móvel.

---

## 4. Gestão de Novas Migrações no Alembic

Sempre que criar ou alterar tabelas em `app/models/`:
1. Importe o novo model em `app/models/__init__.py`.
2. Gere o arquivo de migração automático:
   ```powershell
   .\.venv\Scripts\alembic.exe revision --autogenerate -m "descricao_da_mudanca"
   ```
3. Revise o script gerado em `alembic/versions/` e aplique ao banco:
   ```powershell
   .\.venv\Scripts\alembic.exe upgrade head
   ```

---

## 5. Conexões e Links Relacionados
* **Nota Mestre:** [[11.01 App - Portal do Condômino]]
* **Estrutura de Pastas:** [[11.03 Estrutura de Código e Camadas do Backend]]
* **Gestão de Usuários:** [[11.09 Autenticação e Gestão de Usuários]]
* **Execução de Testes Automatizados:** [[11.10 Testes Automatizados e Qualidade]]
* **Frontend Next.js e PWA:** [[11.13 Frontend, PWA e Design System Editorial]]
