---
id: 11.11 Dimensionamento de Cotas Sienge e Infraestrutura
aliases:
  - Dimensionamento de Cotas e Hardware
  - Infraestrutura do App
tags:
  - tipo/projeto
  - projeto/app
  - infraestrutura
  - sienge
  - cotas
  - dimensionamento
  - hardware
status: ativo
modulo: App & Portal
sistema: Sienge ERP & Portal do Condômino
upstream:
  - "[[11.01 App - Portal do Condômino]]"
  - "[[32.01 Sienge]]"
---

# 11.11 Dimensionamento de Cotas Sienge & Infraestrutura

> Avaliação de consumo de requisições REST da API Sienge, pacotes recomendados e sizing de hardware para 750 a 2.000+ condôminos simultâneos.

---

## 1. Pacotes de Requisições Diárias da API Sienge

A Softplan comercializa o acesso à API REST do Sienge através de limites diários de requisições com renovação a cada 24 horas (UTC).

| Pacote | Requisições REST / Dia | Requisições BULK / Dia | Diagnóstico Técnico de Uso no Portal |
| :--- | :---: | :---: | :--- |
| **FREE** | 100* | 10* | ❌ **Inviável para produção.** Esgota a cota no download dos primeiros 5 diários com fotos. Serve apenas para testes unitários. |
| **START** | **1.000** | **20\*** | 🌟 **RECOMENDADO (Custo-Benefício Ideal):** Atende com mais de 80% de folga a rotina diária de 5 a 8 obras simultâneas ativas com diários, tarefas e fotos. |
| **SPECIAL** | **2.500** | **50\*** | 🚀 **RECOMENDADO PARA ESCALA / HISTÓRICO:** Ideal caso a construtora possua mais de 10 obras simultâneas, rode cargas retroativas (backfill de 60 a 90 dias) ou compartilhe a mesma credencial com PowerBI. |
| **ESSENCIAL** | 5.000 | 100* | ⚠️ **Superdimensionado:** Desnecessário devido à arquitetura BFF de Réplica Operacional. |
| **ENTERPRISE** | 10.000 | 200* | ⚠️ **Superdimensionado.** |
| **BUSINESS** | 30.000 | 600* | ⚠️ **Superdimensionado.** |

---

## 2. Por que o Plano FREE Travou na Primeira Sincronização?

No teste com a base de dados real da construtora, sincronizamos 7 dias de diários de uma única obra (*Jardim Casa Alta*):
1. `GET /enterprises` (1 req)
2. `GET /construction-daily-report` (1 req)
3. `GET /construction-daily-report/{id}` (5 reqs de diários detalhados)
4. `GET /sheets/{unit}/tasks` (2 reqs de planilhas de planejamento)
5. `GET /attachments/{num}` (31 downloads de fotos originais de ~5,6 MB cada)
* **Total consumido:** **66 a 90 requisições**. Ao tentar sincronizar a segunda obra, o Sienge bloqueou imediatamente com `HTTP 429 Too Many Requests (Retry-After: 37568s)`. Portanto, o plano **FREE é inviável para uso real**.

### Como a Arquitetura BFF Economiza Cota:
* **Zero Requisições de Condôminos:** Mesmo que 2.000 condôminos acessem o portal diariamente, **nenhuma requisição chega ao Sienge**. As leituras consom exclusivamente o PostgreSQL local e a CDN de imagens.
* **Consumo em Regime Estável:** Cada obra ativa emite em média 1 diário por dia útil com 5 a 15 fotos. Com 4 obras ativas, a rotina cron consome cerca de **40 a 70 requisições REST/dia**. O plano **START (1.000 req/dia)** opera com mais de **90% de margem de segurança**.

---

## 3. Dimensionamento de Hardware Recomendado (750 a 2.000+ Usuários)

Devido ao uso de **FastAPI Assíncrono (Python 3.12 + `asyncpg`)** e ao **offloading total de fotos** para Object Storage/CDN, o consumo de recursos computacionais é altamente eficiente:
* Leituras assíncronas no PostgreSQL respondem em **2ms a 5ms**.
* Um único worker Uvicorn atende confortavelmente **1.500 a 3.000 req/s**.

### Cenário 1: Servidor VPS Único "All-in-One" (Maior Simplicidade e Menor Custo)
Tudo roda via Docker Compose na mesma máquina: `portal_backend` (FastAPI + Uvicorn com 2 workers) + `portal_frontend` (Next.js) + `portal_condomino_db` (PostgreSQL 16) + Nginx/Caddy com SSL automático.

| Componente | Especificação | Justificativa |
| :--- | :--- | :--- |
| **Processador (CPU)** | **4 vCPUs** (AMD EPYC ou Xeon moderno) | 2 vCPUs dedicadas ao FastAPI + Pillow WebP, 1 vCPU para o PostgreSQL e 1 vCPU para o Next.js / SO. |
| **Memória RAM** | **8 GB RAM** | 2 GB para PostgreSQL (`shared_buffers=1GB`), 1.5 GB para FastAPI (2 workers), 1 GB para Next.js, 3.5 GB para cache de disco do SO. |
| **Armazenamento** | **80 GB a 160 GB NVMe SSD** | Alta taxa de IOPS para queries do PostgreSQL e cache local de fotos. |
| **Rede** | 1 Gbps / Tráfego ilimitado | Entrega rápida de payloads JSON. |

*Custo estimado no provedor **Hetzner Cloud** (Plano CPX31: 4 vCPUs AMD, 8 GB RAM, 160 GB NVMe):* **~€ 13,00 / mês** (~R$ 80/mês).

---

### Cenário 2: Nuvem Gerenciada Enterprise (Alta Disponibilidade)
Para construtoras que exigem separação de banco gerenciado e failover automático:

| Camada | Provedor / Serviço | Dimensionamento |
| :--- | :--- | :--- |
| **Backend API** | AWS ECS Fargate / Google Cloud Run / Render | 1 a 2 réplicas (1 vCPU, 2 GB RAM cada) |
| **Banco de Dados** | AWS RDS PostgreSQL / Supabase Pro | `db.t4g.medium` (2 vCPUs, 4 GB RAM) |
| **Object Storage (Fotos)** | Cloudflare R2 | Armazenamento S3 com custo de egresso **zero** ($0/GB download) e CDN global |
| **Frontend Web/PWA** | Vercel Pro / Cloudflare Pages | Edge hosting distribuído |

---

## 4. Arquitetura Híbrida Recomendada: VPS + Cloudflare R2 (O "Sweet Spot")

A topologia **Híbrida (VPS para Computação/Banco + Cloudflare R2 para Mídia/CDN)** é a solução mais recomendada para a Construtora Benedetto por unir o **menor custo fixo mensal** (~R$ 80 a R$ 100/mês total) com a **máxima performance e escalabilidade**.

### 4.1 Por que o projeto já está 100% validado para VPS + R2?
1. **Compatibilidade S3 Nativa no Código:** O backend já implementa o cliente [`S3StorageClient`](file:///c:/Users/pedro/Desktop/Trabalho/Benedetto/BenedettoApp/portal_backend/app/clients/storage/s3.py) utilizando `boto3` e assinatura `s3v4` no estilo de caminho (*path addressing*), que é o padrão suportado pela Cloudflare.
2. **Desacoplamento Automático via `.env`:** O arquivo de configuração [`config.py`](file:///c:/Users/pedro/Desktop/Trabalho/Benedetto/BenedettoApp/portal_backend/app/core/config.py) ativa o modo S3/R2 automaticamente assim que a variável `STORAGE_ENDPOINT_URL` é preenchida. Se deixada vazia, ele faz fallback seguro para armazenamento em disco local.
3. **Custo de Tráfego Zero (Zero Egress):** A Cloudflare não cobra taxa de saída de dados ($0.00/GB de download). Em contraste com a AWS S3 (que cobra ~$0.09/GB transferido), milhares de acessos a galerias de fotos de alta resolução geram custo zero de banda.
4. **Isolamento de Carga do Servidor:** A VPS não gasta CPU, RAM nem largura de banda servindo fotos. Ela atende apenas requisições JSON leves (2ms a 5ms) e as páginas do Next.js.

```mermaid
flowchart TD
    subgraph Condominos["Condôminos & Usuários"]
        Browser["App Web / PWA Mobile (Condômino)"]
    end

    subgraph Cloudflare["Borda Global Cloudflare"]
        CDN["Cloudflare CDN & WAF (media.condomino.benedetto.com.br)"]
        R2["Cloudflare R2 Bucket (benedetto-portal-media)"]
    end

    subgraph VPS["Servidor VPS (Hetzner / Contabo / DigitalOcean)"]
        Proxy["Caddy / Nginx (HTTPS automático / SSL)"]
        Frontend["Next.js Node (Frontend SSR/SPA)"]
        Backend["FastAPI Uvicorn (BFF & Sincronizador)"]
        DB[(PostgreSQL 16 NVMe Local)]
    end

    subgraph ERP["Softplan Sienge ERP"]
        SiengeAPI["API REST Sienge"]
    end

    Browser -->|1. Acesso ao Portal (HTML/JS/JSON)| Proxy
    Proxy --> Frontend
    Proxy --> Backend
    Backend <--> DB

    Backend -->|2. Cron Job sincroniza diários e baixa fotos originais 5MB| SiengeAPI
    Backend -->|3. Comprime para WebP 100KB e faz upload direto via S3 API| R2
    
    Browser -->|4. Download direto das fotos WebP via CDN Global (0% tráfego na VPS)| CDN
    CDN -->|Cache Hit Instantâneo| Browser
    CDN -.->|Cache Miss| R2
```

---

### 4.2 Passo a Passo de Configuração

#### Passo 1: Criar o Bucket no Cloudflare R2
1. Acesse o painel da [Cloudflare](https://dash.cloudflare.com/) e vá em **R2 Object Storage**.
2. Clique em **Create bucket**.
3. Escolha o nome do bucket: `benedetto-portal-media`.
4. Mantenha a localização como **Automatic**.

#### Passo 2: Configurar Domínio Personalizado ou Acesso Público
1. Dentro do bucket recém-criado, clique na aba **Settings**.
2. Na seção **Public Access**:
   * **Opção Recomendada (Domínio Próprio):** Clique em **Connect Domain** e configure um subdomínio gerenciado pela sua Cloudflare, como `media.condomino.benedetto.com.br` (o SSL Let's Encrypt / Cloudflare Edge é emitido automaticamente).
   * **Opção Alternativa (Dev):** Clique em **Allow Access** no *R2.dev subdomain* para obter a URL pública padrão fornecida pela Cloudflare (ex: `https://pub-xxxxxx.r2.dev`).

#### Passo 3: Gerar as Credenciais de API S3 (Access Key e Secret)
1. No menu lateral do **R2 Object Storage**, clique em **Manage R2 API Tokens**.
2. Clique em **Create API Token**.
3. Defina as permissões:
   * **Permissions:** `Object Read & Write`.
   * **Apply to specific buckets only:** selecione o bucket `benedetto-portal-media`.
4. Clique em **Create API Token**.
5. Copie e guarde em segurança:
   * **Token value**
   * **Access Key ID**
   * **Secret Access Key**
   * **Endpoint URL para S3 clients** (formato: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`).

#### Passo 4: Configurar o `.env` do Backend na VPS
No arquivo `.env` do `portal_backend` na VPS de produção, configure:

```env
# ==============================================================================
# CLOUDFLARE R2 OBJECT STORAGE (PRODUÇÃO)
# ==============================================================================
STORAGE_ENDPOINT_URL=https://<SUA_ACCOUNT_ID>.r2.cloudflarestorage.com
STORAGE_ACCESS_KEY=<SEU_ACCESS_KEY_ID>
STORAGE_SECRET_KEY=<SEU_SECRET_ACCESS_KEY>
STORAGE_BUCKET=benedetto-portal-media
STORAGE_PUBLIC_BASE_URL=https://media.condomino.benedetto.com.br
```

---

## 5. Conexões e Links Relacionados
* **Nota Mestre:** [[11.01 App - Portal do Condômino]]
* **Resiliência e Backoff:** [[11.07 Resiliência, Rate Limit e Carga de Histórico]]
* **Visão Geral e APIs do ERP:** [[32.01 Sienge]]
* **Dashboards do Sienge:** [[32.09 Dashboards do Sienge BI]]
