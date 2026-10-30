---
id: 11.07 Resiliência, Rate Limit e Carga de Histórico
aliases:
  - Resiliência e Rate Limit
  - Carga Histórica e Backfill
tags:
  - tipo/projeto
  - projeto/app
  - backend
  - resiliencia
  - sienge
  - rate-limit
  - backfill
status: ativo
modulo: App & Portal
sistema: Sienge ERP & Portal do Condômino
upstream:
  - "[[11.01 App - Portal do Condômino]]"
---

# 11.07 Resiliência, Rate Limit do Sienge & Carga Histórica

> Mecanismos defensivos de comunicação com o ERP Sienge, controle de backoff exponencial, proteção contra esgotamento de cota diária e procedimento de backfill histórico.

---

## 1. Proteção de Rate Limit e Cota Diária (`HttpSiengeClient`)

O cliente HTTP em `app/clients/sienge/http.py` protege o sistema contra instabilidades e limitações contratuais do ERP:

* **Exponential Backoff com Full Jitter:** Em caso de `HTTP 429` (Rate Limit por minuto), erros de gateway `HTTP 502/503/504` ou falhas de transporte (`httpx.TimeoutException`), o cliente suspende temporariamente a execução aplicando jitter para evitar efeito manada:
  $$\text{Tempo de Espera} = \text{base} \times 2^{\text{tentativa}} + \text{random}(0, 1.5)$$
* **Detecção de Esgotamento de Cota Diária (`SiengeQuotaExceeded`):** Se o Sienge retornar `HTTP 429` com o cabeçalho `Retry-After` superior a `sienge_max_wait_seconds` (configurado para 60s), significa que a cota diária de requisições da construtora esgotou. Em vez de travar o processo dormindo por horas, o cliente lança imediatamente a exceção customizada `SiengeQuotaExceeded`. O `SyncService` captura o erro, faz `COMMIT` do que já foi baixado com sucesso e encerra o log com status `PARCIAL`.

---

## 2. Prevenção de API Drift (`SiengeMapper` + `SiengeMixin`)

A API REST do Sienge pode sofrer alterações de contrato, novos campos ou campos opcionais nulos:
* O `SiengeMapper` realiza extração defensiva através de métodos utilitários (`.get()`, `parse_date()`, `parse_decimal()`), prevenindo exceções de `KeyError` ou falhas de conversão de tipos.
* Todas as tabelas sincronizadas herdam o `SiengeMixin`, que persiste o payload JSON bruto original na coluna `dados_sienge` (`JSONB`). Caso seja necessário consultar ou expor um novo campo que já era retornado pela API, ele pode ser populado diretamente via SQL local, dispensando novas requisições ao Sienge.

---

## 3. Observabilidade e Auditoria (`logs_sincronizacao`)

Toda execução do motor de sincronização (`CRON`, `MANUAL` ou `WEBHOOK`) grava um registro detalhado na tabela `logs_sincronizacao`:
* `status`: `executando`, `sucesso`, `parcial`, `erro`.
* `duracao_ms`: tempo total de processamento em milissegundos.
* `diarios_novos`, `diarios_atualizados`, `fotos_processadas` e `requisicoes_sienge` (auditoria exata de quantas requisições foram consumidas da cota do Sienge).
* `mensagem_erro` e `detalhes`: campo `JSONB` com a lista de falhas isoladas por obra e stack trace completo para depuração.

---

## 4. Janela de Sincronização Deslizante (`SYNC_LOOKBACK_DAYS`)

A rotina de sincronização utiliza uma **janela deslizante de retrospectiva** controlada pela variável de ambiente `SYNC_LOOKBACK_DAYS` (padrão: **`7` dias**):
$$\text{Data Início da Busca} = \text{Data Atual} - \text{SYNC\_LOOKBACK\_DAYS}$$

### 4.1 Por que o padrão é 7 dias?
1. **Blindagem Crítica da Cota da API:** Cada diário detalhado consome no mínimo 1 chamada para dados gerais + 1 chamada para itens de tarefas + 1 chamada para **cada foto original em alta resolução** anexada (5 a 15 fotos de 5 a 10 MB cada). Uma sincronização de 7 dias com 5 diários consome de 70 a 90 requisições. Se a rotina automática (às 06h e 18h) varresse meses inteiros diariamente, a cota da construtora esgotaria na primeira manhã.
2. **Regime Estável:** Diários de obras raramente são alterados após 7 dias de sua criação pelo engenheiro de campo. A janela de 7 dias é mais que suficiente para capturar lançamentos atrasados ou retificações, mantendo o consumo entre **40 e 70 requisições/dia** (plano START com 1.000 req/dia tem mais de 90% de folga).

---

## 5. Como Realizar Carga Inicial Histórica (Backfill de 30 a 90 dias)

Caso você queira importar diários antigos (ex.: do início da obra ou dos últimos meses):

1. **Verifique o saldo da cota Sienge:** Certifique-se de que a cota do plano suporta o volume de diários e fotos antigas.
2. **Ajuste o `.env` do backend:**
   ```env
   SYNC_LOOKBACK_DAYS=30   # ou 60, 90, 180...
   ```
3. **Dispare a sincronização manual:**
   * Via terminal cURL:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/sync -H "Authorization: Bearer <TOKEN_ADMIN>"
     ```
   * Ou pelo botão *"Sincronizar Sienge"* no painel de administração.
4. **Idempotência Garantida:** Graças ao `ON CONFLICT DO UPDATE`, diários e fotos já existentes **não serão duplicados** nem consumirão re-downloads desnecessários.
5. **Restaure o valor padrão:** Finalizada a carga histórica, retorne `SYNC_LOOKBACK_DAYS=7` para preservar a cota nas rotinas automáticas.

---

## 6. Conexões e Links Relacionados
* **Nota Mestre:** [[11.01 App - Portal do Condômino]]
* **Orquestrador SyncService:** [[11.04 Ingestão e Concorrência (SyncService)]]
* **Dimensionamento e Planos da API Sienge:** [[11.11 Dimensionamento de Cotas Sienge e Infraestrutura]]
* **Visão Geral do ERP:** [[32.01 Sienge]]
