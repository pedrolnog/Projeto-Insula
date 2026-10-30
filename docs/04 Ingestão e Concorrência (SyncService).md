---
id: 11.04 Ingestão e Concorrência (SyncService)
aliases:
  - Ingestão e Concorrência
  - SyncService
tags:
  - tipo/projeto
  - projeto/app
  - backend
  - sincronizacao
  - concorrencia
  - advisory-lock
  - sienge
status: ativo
modulo: App & Portal
sistema: Sienge ERP & Portal do Condômino
upstream:
  - "[[11.01 App - Portal do Condômino]]"
---

# 11.04 Ingestão, Concorrência & Idempotência (SyncService)

> Detalhamento do motor de sincronização, controle de concorrência com travas distribuídas, isolamento transacional por obra e upserts idempotentes.

---

## 1. Controle de Concorrência e Dupla Exclusão Mútua

Para evitar que uma sincronização manual (`POST /api/v1/sync`) colida com o disparo automático do Cron Job (`APScheduler` executando às 06h e 18h), ou que múltiplos workers Uvicorn sincronizem a mesma obra simultaneamente, o `SyncService` implementa **dupla trava de exclusão mútua**:

1. **`asyncio.Lock()` (`_process_lock`):** Trava instantânea em memória dentro do mesmo processo Python, impedindo reentrância na mesma instância.
2. **PostgreSQL Advisory Lock (`pg_try_advisory_lock`):** Trava atômica distribuída no nível do banco de dados entre múltiplos processos/containers. Se outro worker já detiver a chave numérica `904202601`, o PostgreSQL retorna `False` imediatamente (sem enfileirar nem travar conexões) e a API responde imediatamente com **`HTTP 409 Conflict`** (`SyncAlreadyRunningError`).

---

## 2. Idempotência e Transações Isoladas por Obra

Toda gravação de entidades sincronizadas utiliza **`INSERT ... ON CONFLICT DO UPDATE` nativo do PostgreSQL** (`sqlalchemy.dialects.postgresql.insert`), garantindo **idempotência absoluta** sobre as chaves naturais do Sienge:
* Obras: `sienge_building_id`
* Diários de Obra: `(obra_id, sienge_diario_id)`
* Tarefas de Diário: `(diario_id, tipo, sienge_item_id)`
* Fotos de Diário: `(diario_id, sienge_attachment_number)`

### Isolamento Transacional de Falhas:
* A sincronização itera sobre cada obra ativa em **sessões/transações isoladas**.
* Caso o processamento de uma obra falhe (ex.: erro de rede no Sienge ou formato de anexo inválido), é realizado o `ROLLBACK` **exclusivamente dessa obra**, permitindo que as demais obras continuem sendo sincronizadas normalmente e gravando o log com status `PARCIAL`.

---

## 3. Diagrama de Sequência de Ingestão

```mermaid
sequenceDiagram
    autonumber
    actor Trigger as Cron Job / Admin
    participant Sync as SyncService
    participant PG as PostgreSQL 16
    participant Sienge as HttpSiengeClient
    participant Mapper as SiengeMapper

    Trigger->>Sync: sincronizar_tudo(origem)
    Sync->>Sync: _process_lock.acquire()
    Sync->>PG: SELECT pg_try_advisory_lock(904202601)
    alt Lock já ocupado por outro worker
        PG-->>Sync: false
        Sync->>Sync: _process_lock.release()
        Sync-->>Trigger: Raise SyncAlreadyRunningError (HTTP 409)
    end
    PG-->>Sync: true
    Sync->>PG: INSERT INTO logs_sincronizacao (status='executando')

    Sync->>Sienge: listar_empreendimentos()
    Sienge-->>Sync: JSON Empreendimentos
    loop Por cada Obra
        Sync->>PG: UPSERT INTO obras ON CONFLICT (sienge_building_id)
        Sync->>Sienge: listar_medicoes() + listar_itens_medicao()
        Sync->>PG: Atualiza obras.percentual_concluido
    end

    loop Por cada Obra (Transação Isolada)
        Sync->>Sienge: listar_diarios(building_id, lookback_days)
        Sync->>PG: SELECT diarios existentes da obra
        loop Por cada Diário novo ou com modifiedAt > sienge_modificado_em
            Sync->>Sienge: obter_diario(building_id, diario_id)
            Sync->>Mapper: mapear_diario() + mapear_tarefas() + mapear_fotos(fase_obra, mapa_unidades)
            Note over Mapper: Se obra em REFORMAS_UNIDADES e foto sem unidade,<br/>define publicado=False (Quarentena)
            Sync->>PG: UPSERT diarios_obra, tarefas_diario, fotos_diario (status='pendente')
        end
        Sync->>PG: COMMIT da Obra (falha em 1 obra faz ROLLBACK só dela)
    end

    Sync->>PG: Atualiza logs_sincronizacao (status, duracao_ms, contadores)
    Sync->>PG: SELECT pg_advisory_unlock(904202601)
    Sync->>Sync: _process_lock.release()
    Sync-->>Trigger: LogSincronizacao finalizado
```

---

## 4. Conexões e Links Relacionados
* **Nota Mestre:** [[11.01 App - Portal do Condômino]]
* **Regras do Ponto X & Quarentena:** [[11.02 Regras de Negócio e Multi-tenancy (Ponto X)]]
* **Processamento de Fotos:** [[11.05 Pipeline de Mídia e Otimização WebP]]
* **Resiliência e Lookback:** [[11.07 Resiliência, Rate Limit e Carga de Histórico]]
* **Integração com Diário de Obra do Sienge:** [[32.10 Diário de Obra Consolidado (RDO)]]
* **Integração com Medição de Obra do Sienge:** [[32.05 Boletim de Medição de Obra]]
