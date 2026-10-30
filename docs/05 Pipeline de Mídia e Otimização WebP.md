---
id: 11.05 Pipeline de Mídia e Otimização WebP
aliases:
  - Pipeline de Mídia
  - Otimização WebP
tags:
  - tipo/projeto
  - projeto/app
  - backend
  - midia
  - pillow
  - webp
  - storage
  - async
status: ativo
modulo: App & Portal
sistema: Sienge ERP & Portal do Condômino
upstream:
  - "[[11.01 App - Portal do Condômino]]"
---

# 11.05 Pipeline de Mídia & Compressão WebP Não-Bloqueante

> Processamento assíncrono de imagens pesadas do canteiro com Pillow, normalização de rotação EXIF, compressão WebP e cache imutável em CDN/R2.

---

## 1. O Desafio de Performance (CPU-Bound vs. Event Loop)

O processamento de imagens (decodificação de JPEGs/PNGs pesados de 5 a 10 MB, correção de rotação EXIF de fotos tiradas por smartphones no canteiro, redimensionamento com filtro bilinear/LANCZOS e compressão WebP) é uma operação puramente **CPU-bound e síncrona**.

Se essa operação fosse executada diretamente no contexto de uma função `async def`, ela bloquearia a thread principal do Event Loop do FastAPI por **50 a 150 ms a cada imagem**. Em uma sincronização com 30 fotos, a API ficaria congelada por até 4,5 segundos, derrubando requisições HTTP de condôminos conectados.

### A Solução: Delegação via `asyncio.to_thread`
O método `MediaService.processar_foto_async` encapsula a lógica síncrona da biblioteca **Pillow** e a despacha para o pool de threads do Python através de:
```python
await asyncio.to_thread(self._processar_foto_sync, bytes_originais)
```
Dessa forma, o Event Loop do FastAPI permanece 100% livre para atender logins e consultas de dados em paralelo.

---

## 2. Etapas da Transformação de Mídia (`_processar_foto_sync`)

1. **Correção de Orientação EXIF (`ImageOps.exif_transpose`):** Analisa a orientação gravada pelos sensores de câmeras de smartphones (ex.: foto na vertical/retrato) e gira os pixels fisicamente, prevenindo que imagens apareçam deitadas ou de cabeça para baixo no portal.
2. **Normalização do Espaço de Cores:** Se a imagem estiver em `RGBA`, `LA` ou `CMYK`, converte de forma segura para `RGB` (com fundo branco caso haja transparência).
3. **Redimensionamento Proporcional (LANCZOS):** Se a maior dimensão da foto ultrapassar `1920px`, a imagem é redimensionada proporcionalmente para caber em uma caixa delimitadora de 1920×1920 pixels com alta nitidez.
4. **Compressão WebP (Qualidade 80):** O arquivo final é serializado em memória como `.webp` com compressão `quality=80`. O tamanho médio do arquivo cai de **~5,6 MB (JPEG original) para ~100 KB (WebP)** (uma redução de ~98% no tráfego de rede).

---

## 3. Armazenamento e Cabeçalho de Cache Imutável

As imagens processadas são salvas no Object Storage (Cloudflare R2, AWS S3 ou disco local) sob uma chave determinística baseada no ID do anexo no Sienge:
```text
obras/{building_id}/diarios/{diario_id}_{attachment_number}.webp
```
Como o conteúdo de uma foto de diário nunca é alterado após o processamento, injeta-se o cabeçalho HTTP:
```http
Cache-Control: public, max-age=31536000, immutable
```
Isso instrui navegadores e PWAs a manter a imagem em cache local por até 1 ano, eliminando re-downloads de fotos já visualizadas.

---

## 4. Diagrama de Sequência do Pipeline de Mídia

```mermaid
sequenceDiagram
    autonumber
    participant Sync as SyncService
    participant Sienge as HttpSiengeClient
    participant Loop as FastAPI Event Loop
    participant Thread as Worker Thread (Pillow)
    participant Storage as S3 / R2 Storage
    participant PG as PostgreSQL 16

    Sync->>PG: SELECT fotos_diario WHERE status = 'pendente' LIMIT 200
    loop Por cada foto pendente (Resiliência individual por foto)
        Sync->>Sienge: baixar_anexo(building_id, diario_id, attachment_number)
        Sienge-->>Sync: bytes_originais (JPEG/PNG 5MB+)
        Sync->>Loop: await media.processar_foto_async(bytes_originais)
        Loop->>Thread: asyncio.to_thread(processar_foto_sync)
        Note over Thread: 1. ImageOps.exif_transpose (corrige rotação)<br/>2. Converte RGBA/CMYK -> RGB<br/>3. Redimensiona máx 1920px (LANCZOS)<br/>4. Comprime para WebP (qualidade 80)
        Thread-->>Loop: ImagemProcessada (.webp ~100KB, largura, altura)
        Sync->>Storage: salvar(chave, bytes_webp, Cache-Control="immutable")
        Storage-->>Sync: url_publica
        Sync->>PG: UPDATE fotos_diario SET status='processada', url=url_publica; COMMIT
    end
```

---

## 5. Conexões e Links Relacionados
* **Nota Mestre:** [[11.01 App - Portal do Condômino]]
* **Orquestrador de Ingestão:** [[11.04 Ingestão e Concorrência (SyncService)]]
* **Regras de Exibição & Quarentena:** [[11.02 Regras de Negócio e Multi-tenancy (Ponto X)]]
* **Dimensionamento e Custos de CDN:** [[11.11 Dimensionamento de Cotas Sienge e Infraestrutura]]
