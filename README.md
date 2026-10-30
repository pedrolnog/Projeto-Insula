# BenedettoApp — Portal do Condômino

Plataforma oficial da **Construtora Benedetto** para acompanhamento da evolução física das obras, diários de obra com fotos em alta resolução (otimizadas em WebP), cronograma e gestão de acabamentos privativos no Ponto X.

---

## 🏛️ Estrutura do Monorepo

```
BenedettoApp/
├── portal_backend/          # API RESTful em FastAPI + SQLAlchemy + PostgreSQL 16 + Alembic
│   ├── app/                 # Código da API (routers, models, schemas, services, jobs)
│   ├── alembic/             # Migrações versionadas do banco de dados
│   ├── scripts/             # Utilitários CLI de gestão de usuários e obras
│   ├── tests/               # Suíte automatizada de testes (pytest + pytest-asyncio)
│   ├── docker-compose.yml   # PostgreSQL 16 em container Docker
│   ├── pyproject.toml       # Dependências e empacotamento Python
│   └── .env.example         # Template de variáveis de ambiente do backend
│
├── portal_frontend/         # Aplicativo Web & PWA em Next.js 15 + React 19 + Tailwind CSS
│   ├── src/                 # Páginas (App Router), componentes e cliente de API
│   ├── public/              # Manifest PWA, ícones e assets estáticos
│   ├── package.json         # Dependências Node.js
│   └── .env.example         # Template de variáveis de ambiente do frontend
│
├── .gitignore               # Regras de exclusão globais do repositório
└── README.md                # Documentação geral de inicialização rápida
```

---

## 🚀 Inicialização Rápida em Desenvolvimento

### 1. Pré-requisitos
* **Python 3.12+** instalado
* **Node.js 20+** e **npm** instalados
* **Docker** e **Docker Compose** ativos (para o PostgreSQL)

---

### 2. Backend (`portal_backend`)

1. Acesse a pasta do backend:
   ```bash
   cd portal_backend
   ```
2. Crie e ative o ambiente virtual:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -e ".[dev]"
   ```
4. Configure as variáveis de ambiente:
   ```bash
   cp .env.example .env
   ```
5. Suba o banco de dados PostgreSQL via Docker:
   ```bash
   docker compose up -d
   ```
6. Aplique as migrações do banco com Alembic:
   ```bash
   alembic upgrade head
   ```
7. Inicie o servidor FastAPI:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   * **Swagger / OpenAPI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 3. Frontend (`portal_frontend`)

1. Em outro terminal, acesse a pasta do frontend:
   ```bash
   cd portal_frontend
   ```
2. Instale as dependências:
   ```bash
   npm install
   ```
3. Configure o arquivo de ambiente local:
   ```bash
   cp .env.example .env.local
   ```
4. Inicie o servidor Next.js em modo de desenvolvimento:
   ```bash
   npm run dev
   ```
   * **Acesse o Portal:** [http://localhost:3000](http://localhost:3000)

---

### 4. Executando os Testes Automatizados

No diretório `portal_backend`:
```bash
pytest -v
ruff check app tests scripts
```

---

## 🔒 Segurança & Conformidade com a LGPD

* **Zero Leakage / Multi-Tenancy:** O condômino só acessa suas próprias obras e unidades cadastradas. Tentativas de acessar dados de terceiros retornam `403 Forbidden`.
* **Proteção de CPF & Rate Limiting:** O endpoint de autenticação possui limitador por IP (*Sliding Window*) e os logs do servidor nunca expõem CPFs em texto claro (`***.456.789-**`).
* **Termo de Privacidade no 1º Acesso:** Registro expresso de consentimento via `POST /api/v1/auth/aceitar-termo-privacidade`.
* **Pipeline de Imagens:** Fotos originais de diários de obra são comprimidas assincronamente para WebP e descarregadas em Object Storage (Cloudflare R2 / S3), garantindo performance e custo zero de transferência de dados (*Zero Egress*).
