---
id: 11.10 Testes Automatizados e Qualidade
aliases:
  - Testes Automatizados
  - Qualidade de Código
tags:
  - tipo/projeto
  - projeto/app
  - testes
  - pytest
  - qualidade
  - linter
  - ruff
status: ativo
modulo: App & Portal
sistema: Sienge ERP & Portal do Condômino
upstream:
  - "[[11.01 App - Portal do Condômino]]"
---

# 11.10 Testes Automatizados & Qualidade de Código

> Execução da suíte de testes de integração, isolamento do banco de dados `portal_condomino_test` e padrões do linter Ruff.

---

## 1. Isolamento Estrito do Banco de Testes

> [!IMPORTANT]
> ### Proteção Total dos Dados Reais
> A fixture assíncrona em `tests/conftest.py` intercepta a conexão e redireciona automaticamente o SQLAlchemy para um banco de dados exclusivo chamado **`portal_condomino_test`** (criado dinamicamente no PostgreSQL se não existir).
>
> Executar a suíte de testes **jamais apaga, altera ou polui** os dados de obras reais sincronizadas do Sienge ou os usuários cadastrados no banco principal `portal_condomino`.

---

## 2. Como Executar os Testes e o Linter

No diretório `portal_backend`:

```powershell
cd C:\Users\pedro\Desktop\Trabalho\Benedetto\BenedettoApp\portal_backend

# 1. Execução detalhada da suíte de testes:
.\.venv\Scripts\python.exe -m pytest -v

# 2. Verificação de estilo e padrões de código:
.\.venv\Scripts\python.exe -m ruff check app tests scripts
```

---

## 3. Cenários Críticos Cobertos pela Suíte

A suíte de testes de integração valida automaticamente:

1. **Conversão de Mídia WebP Assíncrona (`test_media_service_conversao_webp_async`):** Garante que imagens de teste em formato PNG/JPEG sejam lidas, tenham tags EXIF corrigidas e sejam geradas em formato WebP de tamanho reduzido sem travar o event loop.
2. **Backoff e Cota Sienge (`test_http_sienge_client_rate_limit_429_e_quota_exceeded`):** Simula respostas `429` do Sienge, validando a retentativa com backoff e a interrupção imediata via `SiengeQuotaExceeded` quando o tempo de espera excede o limite.
3. **Bloqueio de Concorrência com Advisory Lock (`test_sync_service_bloqueio_concorrencia`):** Valida que duas tentativas simultâneas de sincronização resultem em rejeição imediata com `HTTP 409 Conflict`.
4. **Idempotência Estrita (`test_sync_service_execucao_completa_e_idempotencia`):** Executa duas sincronizações completas sequenciais com a mesma base e valida que nenhum registro duplicado seja criado no PostgreSQL (`ON CONFLICT DO UPDATE`).
5. **Isolamento Multi-Tenant Obra e Unidade (`test_fluxo_completo_auth_e_isolamento_multi_tenancy_obra_e_unidade`):**
   * Valida bloqueio `HTTP 403` quando condômino tenta acessar obra não vinculada.
   * Valida bloqueio `HTTP 403` quando condômino tenta acessar unidade de vizinho.
   * Valida quarentena automática de fotos sem unidade no Ponto X (`publicado = False`).
   * Valida fluxo de liberação pelo painel administrativo.

---

## 4. Conexões e Links Relacionados
* **Nota Mestre:** [[11.01 App - Portal do Condômino]]
* **Setup do Ambiente:** [[11.08 Onboarding e Execução do Ambiente]]
* **Lógica do SyncService:** [[11.04 Ingestão e Concorrência (SyncService)]]
* **Regras do Ponto X:** [[11.02 Regras de Negócio e Multi-tenancy (Ponto X)]]
