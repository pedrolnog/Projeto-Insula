---
id: 11.03 Estrutura de Código e Camadas do Backend
aliases:
  - Estrutura do Backend
  - Camadas do Código
tags:
  - tipo/projeto
  - projeto/app
  - backend
  - fastapi
  - arquitetura
  - diretorios
status: ativo
modulo: App & Portal
sistema: Sienge ERP & Portal do Condômino
upstream:
  - "[[11.01 App - Portal do Condômino]]"
---

# 11.03 Estrutura de Código & Camadas do Backend

> Organização dos diretórios do `portal_backend`, separação estrita de responsabilidades, contratos Pydantic v2 e padrões arquiteturais do FastAPI.

---

## 1. Árvore de Diretórios do Projeto

A estrutura de código do `portal_backend` adota arquitetura modular por responsabilidade técnica:

```text
portal_backend/
├── alembic/                    # Ambiente de migrações assíncronas e histórico de versões SQL
│   ├── versions/               # Scripts de migração gerados (Fase 2 + Ponto X + Índices)
│   └── env.py                  # Configuração asyncpg para o Alembic
├── app/
│   ├── clients/                # Camada de Adaptadores Externos (I/O de Rede e Storage)
│   │   ├── sienge/             # Cliente HTTP Sienge (backoff + 429) e MockSiengeClient
│   │   └── storage/            # Clientes de Object Storage (S3/Cloudflare R2 e Disco Local)
│   ├── core/                   # Núcleo de Configuração, Banco de Dados e Segurança
│   │   ├── config.py           # Variáveis de ambiente tipadas via Pydantic Settings
│   │   ├── database.py         # Engine SQLAlchemy 2.0 Async + Pool dimensionado (20+20)
│   │   └── security.py         # JWT HS256, Bcrypt off-thread e Rate Limiter por IP
│   ├── jobs/                   # Processamento Periódico em Background
│   │   └── scheduler.py        # APScheduler (America/Sao_Paulo, coalesce=True, max_instances=1)
│   ├── models/                 # Modelos ORM SQLAlchemy 2.0 (DeclarativeBase + Mapped[])
│   │   ├── base.py             # Base declarativa, Naming Convention e Mixins (Id, Timestamp, Sienge)
│   │   ├── enums.py            # Enums de domínio (FaseObra, StatusReformaUnidade, StatusFoto, etc.)
│   │   ├── empresa.py          # Tabela `empresas`
│   │   ├── obra.py             # Tabela `obras` (inclui `fase_atual` e `percentual_concluido`)
│   │   ├── unidade.py          # Tabela `unidades` e associativa `usuarios_unidades`
│   │   ├── usuario.py          # Tabela `usuarios` e associativa `usuarios_obras`
│   │   ├── diario.py           # Tabela `diarios_obra` (turnos e ocorrências em JSONB)
│   │   ├── tarefa.py           # Tabela `tarefas_diario` (planejadas + avulsas, geral ou unidade)
│   │   ├── foto.py             # Tabela `fotos_diario` (metadados WebP, `unidade_id` e `publicado`)
│   │   └── log_sincronizacao.py# Tabela `logs_sincronizacao` (auditoria e observabilidade)
│   ├── routers/                # Controladores HTTP FastAPI agrupados por contexto
│   │   ├── health.py           # Liveness/Readiness check (`/api/v1/health`)
│   │   ├── auth.py             # Login por CPF e perfil (`/api/v1/auth`)
│   │   ├── minha_obra.py       # Rotas multi-tenant do condômino (`/api/v1/minha-obra`)
│   │   ├── admin.py            # Curadoria de quarentena e gestão de fase (`/api/v1/admin`)
│   │   └── sync.py             # Disparo manual e histórico de sincronização (`/api/v1/sync`)
│   ├── schemas/                # Contratos Pydantic v2 (Validação de Entrada e Serialização)
│   │   ├── auth.py             # LoginRequest (normaliza CPF), TokenResponse, UsuarioResumoSchema
│   │   └── obra.py             # MinhaObraResponse, MinhaUnidadeDetalheResponse, DiarioObraSchema, etc.
│   ├── services/               # Regras de Negócio, Ingestão, Mapeamento e Mídia
│   │   ├── sync_service.py     # Orquestrador de sincronização com PostgreSQL Advisory Lock
│   │   ├── sienge_mapper.py    # Normalizador defensivo de payloads Sienge + Quarentena Ponto X
│   │   ├── media_service.py    # Conversão CPU-bound Pillow WebP off-thread (`asyncio.to_thread`)
│   │   └── seed_service.py     # Seed idempotente para desenvolvimento/homologação
│   └── main.py                 # Entrypoint ASGI, Lifespan, CORS e Middleware de Cache-Control
└── tests/                      # Suíte de testes automatizados (pytest + pytest-asyncio + httpx)
```

---

## 2. Responsabilidades das Camadas

### 2.1 Camada de Clientes (`app/clients/`)
* **Sienge Client:** Abstrai a comunicação HTTPS com o ERP Sienge (`HttpSiengeClient`). Implementa retry automático com backoff exponencial e full jitter em respostas `429/502/503/504`. Possui versão de mock (`MockSiengeClient`) para desenvolvimento local offline e testes.
* **Storage Client:** Abstrai o armazenamento binário de fotos WebP (`S3StorageClient` compatível com Cloudflare R2 e AWS S3, e `LocalStorageClient` para testes locais em disco).

### 2.2 Camada Core (`app/core/`)
* **`config.py`:** Configurações centralizadas e tipadas lidas de variáveis de ambiente (`.env`) usando `pydantic-settings`.
* **`database.py`:** Criação da engine assíncrona do SQLAlchemy 2.0 (`create_async_engine`) com driver `asyncpg`, pool dimensionado (20 conexões base + até 20 de overflow) e pool pre-ping ativo.
* **`security.py`:** Funções para criação/decodificação de tokens JWT (HS256) e hashing de senhas via Bcrypt delegados para threads (`asyncio.to_thread`).

### 2.3 Camada de Modelos (`app/models/`)
* Declaração de tabelas com tipagem estrita `Mapped[T]` do SQLAlchemy 2.0.
* Reutilização de mixins: `IdMixin` (inteiro autoincremental), `TimestampMixin` (`criado_em` e `atualizado_em`), e `SiengeMixin` (`sienge_id`, `sienge_modificado_em` e `dados_sienge JSONB` para proteção contra *API Drift*).

### 2.4 Camada de Serviços (`app/services/`)
* **`sync_service.py`:** Contém o algoritmo principal de sincronização de dados do Sienge, controle de concorrência com travas advisory e orquestração de transações.
* **`sienge_mapper.py`:** Transforma payloads JSON brutos do Sienge em entidades do banco local, aplicando normalização de datas, valores monetários e regras do Ponto X.
* **`media_service.py`:** Pipeline assíncrono de decodificação, rotação EXIF, redimensionamento e conversão WebP.

---

## 3. Conexões e Links Relacionados
* **Nota Mestre:** [[11.01 App - Portal do Condômino]]
* **Ingestão e Advisory Lock:** [[11.04 Ingestão e Concorrência (SyncService)]]
* **Processamento de Mídia:** [[11.05 Pipeline de Mídia e Otimização WebP]]
* **Rotas do Condômino:** [[11.06 Fluxo de Leitura e Endpoints do Condômino]]
* **Configuração e Execução:** [[11.08 Onboarding e Execução do Ambiente]]
* **Modelagem Relacional e Índices:** [[11.12 Modelagem de Dados Relacional e Otimizações SQL]]
* **Camada Frontend (Next.js):** [[11.13 Frontend, PWA e Design System Editorial]]
* **Segurança e LGPD:** [[11.14 Conformidade com a LGPD e Segurança de Dados]]
