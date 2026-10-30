# BenedettoApp — Portal do Condômino

<div align="center">

![Next.js](https://img.shields.io/badge/Next.js-15.5-black?style=for-the-badge&logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/React-19.1-blue?style=for-the-badge&logo=react&logoColor=61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=yellow)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Cloudflare R2](https://img.shields.io/badge/Cloudflare_R2-S3_Compatible-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)

**Plataforma Web & PWA de alta fidelidade e performance para acompanhamento de obras, diários de engenharia e gestão de reformas privativas no Ponto X.**

[Arquitetura](#-arquitetura--fluxo-de-dados) •
[Funcionalidades](#-principais-funcionalidades) •
[Como Executar](#-guia-de-inicialização-rápida) •
[Comandos CLI](#-gestão-de-usuários-e-obras-cli) •
[LGPD & Segurança](#-segurança-multi-tenancy--lgpd) •
[Produção](#-deploy-em-produção-vps--cloudflare-r2)

</div>

---

## 🏗️ Visão Geral

O **Portal do Condômino Benedetto** foi desenvolvido para transformar a experiência dos clientes e investidores de empreendimentos imobiliários. Integrado à API REST do **ERP Sienge**, o portal adota a arquitetura de **Réplica Operacional Local (BFF)**:
* **Zero Custo de Cota:** Nenhum acesso de condômino consome requisições da cota diária do Sienge.
* **Latência Ultrabaixa (2ms a 5ms):** As leituras consultam exclusivamente o banco PostgreSQL 16 com indexação assíncrona.
* **Pipeline de Mídia Otimizado:** Fotos de alta resolução (5 MB a 10 MB) são convertidas em *background* para **WebP (~100 KB)** e servidas com cache perpétuo via CDN global com **custo zero de download (Zero Egress)**.

---

## ✨ Principais Funcionalidades

### 📱 Para o Condômino
* **Visão Geral da Obra:** Indicadores de evolução física geral com barra de progresso, data de entrega, endereço e histórico de diários.
* **Diários de Obra com Fotos em Alta Resolução:** Galeria com visualizador *Lightbox*, tags de localização técnica e descrição dos serviços.
* **Suporte Multi-Obra:** Condôminos com unidades em mais de um empreendimento alternam entre obras no topo da aplicação com 1 clique.
* **O "Ponto X" (Reformas das Unidades):** Quando a obra atinge a fase de acabamento, o app abre automaticamente na visão privativa do apartamento do condômino, exibindo percentual da reforma, parecer da engenharia e fotos exclusivas da unidade.

### 🛠️ Para a Engenharia & Administração
* **Ajuste Rápido de Evolução Física:** Modal administrativo no próprio app para atualizar em tempo real o percentual concluído e a fase da obra.
* **Quarentena & Curadoria Automática:** Fotos sem identificação de apartamento enviadas durante o Ponto X entram em quarentena (`publicado=false`), evitando que fotos de reformas privadas vazem no feed comum.
* **Disparo Manual e Sincronização Agendada:** Ingestão periódica via `APScheduler` (às 06h e 18h) com suporte a retentativas exponenciais (*Full Jitter*) e bloqueio de concorrência (*PostgreSQL Advisory Lock*).

---

## 🏛️ Estrutura do Monorepo

```
BenedettoApp/
├── portal_backend/                  # API RESTful em FastAPI + SQLAlchemy Async + Alembic
│   ├── alembic/                     # Migrações versionadas do PostgreSQL
│   ├── app/
│   │   ├── clients/                 # Integrações externas (Sienge HTTP/Mock e Storage S3/Local)
│   │   ├── core/                    # Configurações Pydantic, Conexão DB, Segurança e JWT
│   │   ├── jobs/                    # Agendador periódico de ingestão (APScheduler)
│   │   ├── models/                  # Tabelas SQLAlchemy (ORM)
│   │   ├── routers/                 # Rotas da API (/auth, /minha-obra, /admin, /sync, /health)
│   │   ├── schemas/                 # Validações e contratos Pydantic v2
│   │   └── services/                # Regras de negócio (SyncService, MediaService, SeedService)
│   ├── docs/                        # Documentação técnica do modelo de dados
│   ├── scripts/                     # Utilitário CLI completo de gestão de usuários e obras
│   ├── tests/                       # Suíte automatizada com banco isolado (pytest)
│   ├── docker-compose.yml           # Container PostgreSQL 16
│   ├── pyproject.toml               # Dependências do backend Python
│   └── .env.example                 # Template de variáveis do backend
│
├── portal_frontend/                 # Frontend Web SPA & PWA (Next.js 15 + React 19)
│   ├── public/                      # Manifest PWA, ícones da marca e assets estáticos
│   ├── src/
│   │   ├── app/                     # Next.js App Router (Página inicial, login, layout)
│   │   ├── components/              # Componentes UI (DiarioCard, Lightbox, Logo, Modais)
│   │   └── lib/                     # Cliente de API tipado com fetch assíncrono
│   ├── package.json                 # Dependências do frontend
│   └── .env.example                 # Template de variáveis do frontend
│
├── .gitignore                       # Regras de exclusão do Git para o Monorepo
└── README.md                        # Guia principal do projeto
```

---

## 🚀 Guia de Inicialização Rápida

### 1. Pré-requisitos
* **Python 3.12+**
* **Node.js 20+** e **npm**
* **Docker** e **Docker Compose**

---

### 2. Configurando e Rodando o Backend

1. **Acesse a pasta do backend:**
   ```bash
   cd portal_backend
   ```

2. **Crie e ative o ambiente virtual:**
   ```powershell
   # Windows (PowerShell):
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux/macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure o arquivo de ambiente:**
   ```bash
   cp .env.example .env
   ```
   *(Em desenvolvimento local, `SIENGE_USE_MOCK=true` permite rodar tudo de forma 100% offline).*

5. **Suba o banco de dados PostgreSQL via Docker:**
   ```bash
   docker compose up -d
   ```

6. **Aplique as migrações do banco com Alembic:**
   ```bash
   alembic upgrade head
   ```

7. **Inicie o servidor FastAPI:**
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   * **Documentação Swagger Interativa:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   * **Health Check:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

### 3. Configurando e Rodando o Frontend

1. **Em outro terminal, acesse a pasta do frontend:**
   ```bash
   cd portal_frontend
   ```

2. **Instale as dependências:**
   ```bash
   npm install
   ```

3. **Configure as variáveis de ambiente:**
   ```bash
   cp .env.example .env.local
   ```
   *(Verifique se `NEXT_PUBLIC_API_URL=http://localhost:8000` está definido no `.env.local`).*

4. **Inicie o servidor de desenvolvimento:**
   ```bash
   npm run dev
   ```
   * **Acesse a Aplicação:** [http://localhost:3000](http://localhost:3000)

---

## 🔑 Credenciais de Demonstração (Ambiente Mock)

Quando `SIENGE_USE_MOCK=true`, o sistema disponibiliza perfis de teste pré-configurados:

| Perfil | CPF | Senha | Acesso e Finalidade |
| :--- | :---: | :---: | :--- |
| **Administrador** | `000.000.000-00` | `admin123` | Acesso irrestrito a todas as obras, quarentena de fotos e sincronização. |
| **Condômino (João)** | `111.222.333-44` | `benedetto123` | Vinculado à Obra 101 e proprietário de 2 unidades (`Apto 302` e `Apto 501`). |
| **Condômino (Vizinho)** | `222.333.444-55` | `benedetto123` | Dono do `Apto 404` (testa o isolamento de privacidade no Ponto X). |

> [!WARNING]
> Em produção (`SIENGE_USE_MOCK=false`), os usuários mock são automaticamente desabilitados por segurança.

---

## 💻 Gestão de Usuários e Obras (CLI)

O utilitário `scripts/criar_usuario.py` permite gerenciar perfis, permissões e obras diretamente pelo terminal:

```powershell
cd portal_backend

# 1. Menu Interativo Guiado (Recomendado):
.\.venv\Scripts\python.exe scripts/criar_usuario.py

# 2. Listar todos os usuários:
.\.venv\Scripts\python.exe scripts/criar_usuario.py --listar

# 3. Listar obras cadastradas e IDs:
.\.venv\Scripts\python.exe scripts/criar_usuario.py --listar-obras

# 4. Criar Administrador:
.\.venv\Scripts\python.exe scripts/criar_usuario.py --cpf 09135315458 --nome "Engenheiro Benedetto" --senha "SenhaSegura123" --perfil admin

# 5. Criar Condômino vinculado a múltiplas obras:
.\.venv\Scripts\python.exe scripts/criar_usuario.py --cpf 12345678900 --nome "Carlos Santos" --senha "benedetto123" --perfil condomino --obras 1 2

# 6. Atualizar a evolução física e fase de uma obra:
.\.venv\Scripts\python.exe scripts/criar_usuario.py --definir-obra-percentual 1 18.5
.\.venv\Scripts\python.exe scripts/criar_usuario.py --definir-obra-fase 1 reformas_unidades
```

---

## 🛡️ Segurança, Multi-Tenancy & LGPD

O projeto foi construído em estrita conformidade com a **LGPD (Lei nº 13.709/2018)**:

1. **Blindagem contra Vazamento Cruzado:**
   * Nenhum condômino consegue visualizar o nome, CPF, e-mail ou lista de unidades de outros compradores.
   * A rota de detalhe de unidades (`GET /api/v1/minha-obra/unidades/{id}`) valida a propriedade via banco de dados e retorna **`HTTP 403 Forbidden`** para qualquer tentativa de acesso indevido.
2. **Base Legal Adequada (Art. 7º, V da LGPD):**
   * O tratamento de dados baseia-se na **Execução de Contrato** de compra e venda de imóvel na planta.
   * No 1º login, o condômino visualiza o **Modal de Termos de Uso e Privacidade**, registrando o consentimento com carimbo de data/hora no banco de dados.
3. **Proteção do CPF e Credenciais:**
   * Rate limiting no login com *Sliding Window* por IP contra força bruta.
   * Senhas armazenadas com **Bcrypt (12 rounds)** geradas em *threads* separadas.
   * Logs sanitizados automaticamente (`mascarar_cpf()`) exibindo apenas `***.456.789-**`.

---

## 🧪 Testes Automatizados e Qualidade

O backend possui uma suíte completa de testes de integração com banco de dados dedicado e isolado (`portal_condomino_test`):

```powershell
cd portal_backend

# Rodar todos os testes automatizados:
.\.venv\Scripts\python.exe -m pytest -v

# Rodar verificação de lint e boas práticas (Ruff):
.\.venv\Scripts\python.exe -m ruff check app tests scripts
```

---

## 🌐 Deploy em Produção (VPS + Cloudflare R2)

A topologia recomendada é **Híbrida**:
* **VPS (Hetzner / Contabo / DigitalOcean):** Executa Next.js, FastAPI e PostgreSQL 16 via Docker Compose com Caddy ou Nginx (SSL automático).
* **Cloudflare R2:** Armazena 100% das fotos WebP com custo de tráfego zero (**Zero Egress**).

Para ativar o Cloudflare R2, basta configurar as variáveis no `.env` do backend:
```env
STORAGE_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
STORAGE_ACCESS_KEY=<SEU_R2_ACCESS_KEY>
STORAGE_SECRET_KEY=<SEU_R2_SECRET_KEY>
STORAGE_BUCKET=benedetto-portal-media
STORAGE_PUBLIC_BASE_URL=https://media.condomino.benedetto.com.br
```

---

## 📄 Licença

Propriedade exclusiva da **Construtora Benedetto**. Todos os direitos reservados.
