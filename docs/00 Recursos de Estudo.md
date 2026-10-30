---
id: 11.00 Recursos de Estudo
aliases:
  - Recursos de Estudo
  - Trilha de Formação do App
tags:
  - tipo/recurso
  - projeto/app
  - estudo
  - arquitetura
  - referencias
status: ativo
modulo: App & Portal
upstream:
  - "[[MDC Portal do Condômino]]"
  - "[[11.01 App - Portal do Condômino]]"
---

# 11.00 Recursos de Estudo & Referências Técnicas

> Trilha formativa de conceitos arquiteturais, boas práticas de engenharia de software e referências bibliográficas aplicadas ao ecossistema do Portal do Condômino.

---

### Lista de Conceitos para Estudar

#### Arquitetura & System Design
* Backend for Frontend (BFF)
* Operational Data Store (ODS) / Réplica de Leitura
* Clean Architecture / Arquitetura Hexagonal (Ports & Adapters)
* C4 Model
* Architecture Decision Records (ADR)
* Multi-tenancy (Estratégias de isolamento de dados)

#### APIs & Integrações
* RESTful API Design & OpenAPI (Swagger)
* Webhooks vs. Polling
* Idempotência & Idempotency Keys
* Rate Limiting & Throttling
* Exponential Backoff & Jitter
* Circuit Breaker Pattern

#### Backend (Python) & Processamento Assíncrono
* Asynchronous I/O (`asyncio` no Python)
* FastAPI & Pydantic
* Background Tasks & Message Queues (Celery / BullMQ / Redis)
* Cron Jobs & Schedulers (APScheduler)

#### Banco de Dados, Cache & Mídia
* Modelagem Relacional (PostgreSQL)
* Índices e Otimização de Consultas
* Estratégias de Cache (Cache-Aside, Write-Through)
* Object Storage (S3 / R2) & CDN (Content Delivery Network)
* Compressão e Otimização de Imagens (WebP, Thumbnails, Lazy Loading)

#### Segurança & Autenticação
* Autenticação Stateless (JWT - JSON Web Tokens)
* Role-Based Access Control (RBAC)
* Row-Level Security (RLS)
* OWASP Top 10 API Security Risks
* Boas Práticas de LGPD para Aplicações Web/Mobile

#### Frontend & Estratégia de Entrega
* Progressive Web Apps (PWA) & Service Workers
* Mobile-First Responsive Design
* Client-Side Rendering (CSR) vs. Server-Side Rendering (SSR)
* SWR / React Query (Stale-While-Revalidate)

---

### Lista de Recursos

#### 📚 Livros
* **Designing Data-Intensive Applications** — *Martin Kleppmann* (Referência fundamental de system design, sincronização e resiliência)
* **Arquitetura Limpa (Clean Architecture)** — *Robert C. Martin*
* **Construindo Microserviços** — *Sam Newman* (Excelente cobertura dos padrões BFF, integração e isolamento)
* **API Design Patterns** — *JJ Geewax*
* **Architecture Patterns with Python** — *Harry Percival & Bob Gregory* (Disponível gratuitamente online em [cosmicpython.com](https://www.cosmicpython.com/))

#### 🌐 Artigos & Documentações Oficiais
* [Documentação Oficial do FastAPI](https://fastapi.tiangolo.com/) (Tutoriais de async, background tasks e segurança)
* [System Design Primer (GitHub - donnemartin)](https://github.com/donnemartin/system-design-primer) (Repositório essencial com diagramas e resumos de arquitetura de larga escala)
* [Padrão BFF - Martin Fowler](https://martinfowler.com/articles/bliki/BackendsForFrontends.html)
* [Guia de PWA - MDN Web Docs](https://developer.mozilla.org/pt-BR/docs/Web/Progressive_web_apps)
* [Documentação de APIs do Sienge](https://api.sienge.com.br/) (Referência direta dos endpoints e regras de integração)
* [The C4 Model for Visualising Software Architecture](https://c4model.com/)

#### 🎥 Vídeos & Canais
* **ByteByteGo (Alex Xu)** (YouTube) — Vídeos visuais curtos sobre System Design, Rate Limiting, Caching e Webhooks vs. Polling.
* **Fábio Akita (Akitando)** (YouTube) — Séries sobre fundamentos de arquitetura, redes, banco de dados e engenharia de software.
* **Full Cycle / Rodrigo Branas** (YouTube) — Aulas sobre Arquitetura Hexagonal, Clean Architecture e padrões de microsserviços.
* **ArjanCodes** (YouTube) — Padrões de design de software e arquitetura aplicados especificamente a Python moderno.
* **Tiangolo (Sebastián Ramírez)** (Palestras no YouTube / PyCon) — Apresentações sobre construção de APIs assíncronas com FastAPI.

---

## Conexões
- **MDC do Projeto:** [[MDC Portal do Condômino]]
- **Nota Mestre de Arquitetura:** [[11.01 App - Portal do Condômino]]
- **MDC Geral do Vault:** [[MDC Benedetto]]
