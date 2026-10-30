---
id: 11.02 Regras de Negócio e Multi-tenancy (Ponto X)
aliases:
  - Multi-tenancy e Ponto X
  - Regras de Negócio do App
tags:
  - tipo/projeto
  - projeto/app
  - regras-de-negocio
  - multi-tenant
  - ponto-x
  - seguranca
status: ativo
modulo: App & Portal
sistema: Sienge ERP & Portal do Condômino
upstream:
  - "[[11.01 App - Portal do Condômino]]"
---

# 11.02 Regras de Negócio & Multi-Tenancy (O "Ponto X")

> Regras críticas de domínio, isolamento rigoroso de condôminos e política de inversão de risco para fotos de unidades privativas.

---

## 1. Isolamento Estrito em Dois Níveis (Obra e Unidade)

O sistema implementa **Multi-Tenancy em duas camadas** no PostgreSQL, garantindo proteção contra vulnerabilidades de *Broken Object Level Authorization (BOLA / IDOR)*:

1. **Nível 1 — Vínculo Condômino $\leftrightarrow$ Obra (`usuarios_obras`):**
   * Um condômino pode investir em 1 ou mais obras.
   * Toda rota em `/api/v1/minha-obra` valida se o `obra_id` solicitado pertence ao conjunto de obras vinculadas ao `usuario_atual.id` em `usuarios_obras`. Tentativas de consultar `obra_id` de terceiros retornam imediatamente **`HTTP 403 Forbidden`**.
2. **Nível 2 — Vínculo Condômino $\leftrightarrow$ Unidade (`usuarios_unidades`):**
   * Dentro de uma mesma obra, existem dezenas ou centenas de apartamentos (`unidades`), e um mesmo condômino pode ser proprietário de **1 ou mais unidades** (ex.: `Apto 302` e `Apto 501`).
   * **Regra Inegociável de Privacidade:** Condôminos **jamais** podem ver unidades uns dos outros, nem saber quais unidades pertencem a vizinhos. O endpoint `/api/v1/minha-obra/unidades/{unidade_id}` exige vínculo explícito na tabela `usuarios_unidades` (ou perfil `ADMIN`), retornando **`HTTP 403 Forbidden`** para qualquer tentativa de acesso cruzado.

---

## 2. A Transição do "Ponto X" (`FaseObra`)

O ciclo de vida de uma obra no portal é controlado pelo enum `FaseObra` (`obras.fase_atual`):

| Fase (`FaseObra`) | Comportamento no Portal do Condômino |
| :--- | :--- |
| **`ESTRUTURAL_GERAL`** *(Fase 1)* | A obra está em fundação, supraestrutura, concretagem de lajes e fachada. Todos os condôminos daquela obra acompanham a **Visão Geral do Edifício** como tela principal. |
| **`REFORMAS_UNIDADES`** *(Ponto X)* | **Marco de Inflexão:** A obra entrou na fase de acabamentos internos dos apartamentos (revestimentos, porcelanato, gesso, bancadas). O aplicativo passa a abrir **automaticamente na aba "Minha Unidade"** (ou *"Minhas Unidades"*, com seletor de imóveis caso o condômino possua mais de um), exibindo percentual de reforma individual (`percentual_reforma`), status (`StatusReformaUnidade`), parecer da engenharia (`observacoes_reforma`), serviços executados e fotos exclusivas do interior do apartamento. A evolução geral do edifício permanece acessível como aba secundária. |
| **`ENTREGA`** *(Fase Final)* | Fase de vistorias finais e entrega de chaves, mantendo o foco principal na unidade autônoma do condômino. |

---

## 3. Privacidade de Conteúdo e Quarentena Automática

Tanto a tabela `fotos_diario` quanto `tarefas_diario` possuem a chave estrangeira opcional `unidade_id` (`FK -> unidades.id`), e `fotos_diario` possui a flag booleana `publicado`:

* **`unidade_id IS NULL` e `publicado == True`:** Conteúdo **coletivo/geral do edifício** (fachada, hall, piscina, estrutura). Visível na aba *"Edifício Geral"* para todos os condôminos daquela obra.
* **`unidade_id == X` e `publicado == True`:** Conteúdo **privado e exclusivo da unidade `X`**. Jamais aparece nos diários coletivos do edifício (`WHERE unidade_id IS NULL`); aparece **unicamente** para os titulares da unidade `X` na aba *"Minha Unidade"*.

> [!CAUTION]
> ### Política de Inversão de Risco no Ponto X (Quarentena Automática)
> Em canteiro de obras real, um engenheiro pode anexar no Sienge uma foto do interior de um apartamento esquecendo de preencher o campo `location` (ex.: deixando em branco ou escrevendo apenas *"vistoria bancada"*).
>
> Para eliminar 100% do risco de uma foto privada de apartamento vazar no feed geral do condomínio:
> * Quando `obra.fase_atual` está em `REFORMAS_UNIDADES` ou `ENTREGA`, qualquer foto vinda do Sienge que **não tiver correspondência clara com uma unidade** (`unidade_id = None`) é salva automaticamente com **`publicado = False` (Retida em Quarentena)**.
> * Fotos com `publicado = False` são invisíveis para todos os condôminos.
> * No **Painel de Curadoria Rápida do Admin** (`GET /api/v1/admin/fotos-quarentena` e `PATCH /api/v1/admin/fotos/{id}/classificar`), o engenheiro/administrador aprova a foto com **1 clique**, escolhendo se ela é de *"Área Comum / Edifício Geral"* (`unidade_id=None, publicado=True`) ou vinculando-a ao apartamento correto (`unidade_id=X, publicado=True`).

---

## 4. Gestão da Evolução Física Geral da Obra e Transição de Fase

### 4.1 Por que o avanço físico geral pode iniciar em 0.00%?
* No ERP Sienge, as APIs de Empreendimentos (`/enterprises`) e de Diários de Obra (`/construction-daily-report`) **não calculam nem retornam o percentual de conclusão global da obra**.
* O Sienge armazena medições de progresso físico exclusivamente no módulo de **Acompanhamentos de Obra** (`/building-projects/progress-logs`). Se a construtora não cadastrou medições formais nesse módulo ou se a cota diária do Sienge esgotou, a API retorna lista vazia.
* Por esse motivo, o sistema possui **controle soberano do Administrador** para definir e ajustar o avanço físico de qualquer obra a qualquer momento.

### 4.2 Formas de Atualização do Percentual e Fase:
1. **Pelo Aplicativo Web / Painel Admin (1 Clique):**
   * Ao lado do indicador **"Evolução Física Geral"** no card do empreendimento, o Administrador clica em **"Ajustar"** (ícone de lápis).
   * Define o percentual (ex.: `14.50%`) e a fase da obra (`Estrutural Geral`, `Reformas das Unidades` ou `Entrega`) e salva instantaneamente.
2. **Pelo Terminal CLI (`scripts/criar_usuario.py`):**
   ```powershell
   python scripts/criar_usuario.py --definir-obra-percentual 128 14.5
   python scripts/criar_usuario.py --definir-obra-fase 128 reformas_unidades
   ```
3. **Pela API REST Administrativa (`PATCH /api/v1/admin/obras/{obra_id}`):**
   ```bash
   curl -X PATCH http://localhost:8000/api/v1/admin/obras/128 \
     -H "Authorization: Bearer <TOKEN_ADMIN>" \
     -H "Content-Type: application/json" \
     -d '{"percentual_concluido": 14.5, "fase_atual": "estrutural_geral"}'
   ```

---

## 5. Conexões e Links Relacionados
* **Nota Mestre do Projeto:** [[11.01 App - Portal do Condômino]]
* **Mapeamento de Ingestão:** [[11.04 Ingestão e Concorrência (SyncService)]]
* **Endpoints de Leitura:** [[11.06 Fluxo de Leitura e Endpoints do Condômino]]
* **Gestão de Acesso e Perfis:** [[11.09 Autenticação e Gestão de Usuários]]
* **Modelagem e Índices Parciais:** [[11.12 Modelagem de Dados Relacional e Otimizações SQL]]
* **Frontend e Abas no Ponto X:** [[11.13 Frontend, PWA e Design System Editorial]]
* **Conformidade LGPD:** [[11.14 Conformidade com a LGPD e Segurança de Dados]]
* **Conceito de Diário de Obra (ERP):** [[32.10 Diário de Obra Consolidado (RDO)]]
