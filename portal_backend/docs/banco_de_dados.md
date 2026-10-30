# Banco de Dados: Estrutura, Índices e Evolução (`PostgreSQL 16`)

## 1. Diagrama Entidade-Relacionamento (ERD)

```mermaid
erDiagram
    EMPRESAS ||--o{ OBRAS : "possui"
    OBRAS ||--o{ UNIDADES : "contém (Ponto X)"
    OBRAS ||--o{ DIARIOS_OBRA : "registra"
    OBRAS ||--o{ USUARIOS_OBRAS : "vincula"
    USUARIOS ||--o{ USUARIOS_OBRAS : "investe em"
    USUARIOS ||--o{ USUARIOS_UNIDADES : "titular de"
    UNIDADES ||--o{ USUARIOS_UNIDADES : "pertence a"
    DIARIOS_OBRA ||--o{ TAREFAS_DIARIO : "executa"
    DIARIOS_OBRA ||--o{ FOTOS_DIARIO : "anexa"
    UNIDADES ||--o{ TAREFAS_DIARIO : "reforma (opcional)"
    UNIDADES ||--o{ FOTOS_DIARIO : "reforma (opcional)"
    OBRAS ||--o{ LOGS_SINCRONIZACAO : "audita (opcional)"

    EMPRESAS {
        int id PK
        int sienge_id UK
        varchar nome
        varchar cnpj
        boolean ativo
    }

    OBRAS {
        int id PK
        int empresa_id FK
        int sienge_building_id UK
        int sienge_enterprise_id
        varchar nome
        varchar fase_atual "estrutural_geral | reformas_unidades | entrega"
        numeric percentual_concluido
        boolean visivel_portal
        jsonb dados_sienge
    }

    UNIDADES {
        int id PK
        int obra_id FK
        varchar identificador "Ex: Apto 302 - Torre A"
        int sienge_unit_id
        varchar status_reforma "nao_iniciada | em_andamento | concluida"
        numeric percentual_reforma
        text observacoes_reforma
    }

    USUARIOS {
        int id PK
        varchar cpf UK "11 dígitos"
        varchar nome
        varchar perfil "condomino | admin"
        boolean ativo
        timestamptz ultimo_login_em
        timestamptz termo_privacidade_aceito_em "Conformidade LGPD"
    }

    DIARIOS_OBRA {
        int id PK
        int obra_id FK
        int sienge_diario_id "UK com obra_id"
        date data
        numeric indice_pluviometrico
        jsonb turnos
        jsonb ocorrencias
        boolean publicado
        jsonb dados_sienge
    }

    TAREFAS_DIARIO {
        int id PK
        int diario_id FK
        int unidade_id FK "NULL = Geral | ID = Reforma Unidade"
        varchar tipo "planejada | avulsa"
        int sienge_item_id
        varchar descricao
        numeric quantidade
    }

    FOTOS_DIARIO {
        int id PK
        int diario_id FK
        int unidade_id FK "NULL = Geral | ID = Reforma Unidade"
        int sienge_attachment_number
        varchar status "pendente | processada | erro"
        boolean publicado "False = Retida em Quarentena (Ponto X)"
        varchar url
    }

    LOGS_SINCRONIZACAO {
        int id PK
        varchar origem "cron | manual | webhook"
        varchar status "executando | sucesso | parcial | erro"
        int duracao_ms
        int requisicoes_sienge
        jsonb detalhes
    }
```

---

## 2. Organização do Código (`app/models/`)

| Arquivo | Conteúdo |
| :--- | :--- |
| `base.py` | `Base`, convenção determinística de nomes de constraints e mixins (`IdMixin`, `TimestampMixin`, `SiengeMixin`) |
| `enums.py` | Enums de domínio (`PerfilUsuario`, `FaseObra`, `StatusReformaUnidade`, `TipoTarefa`, `StatusFoto`, `StatusSincronizacao`, `OrigemSincronizacao`) gravados como `VARCHAR` |
| `empresa.py` | Tabela `empresas` |
| `obra.py` | Tabela `obras` (inclui `fase_atual` para controle do Ponto X e `percentual_concluido`) |
| `unidade.py` | Tabela `unidades` e tabela associativa `usuarios_unidades` |
| `usuario.py` | Tabela `usuarios` (inclui `termo_privacidade_aceito_em`) e tabela associativa `usuarios_obras` |
| `diario.py` | Tabela `diarios_obra` (turnos e ocorrências em `JSONB`) |
| `tarefa.py` | Tabela `tarefas_diario` (vinculada ao diário e opcionalmente a uma `unidade_id`) |
| `foto.py` | Tabela `fotos_diario` (metadados WebP, `unidade_id`, `publicado` e índices parciais PostgreSQL) |
| `log_sincronizacao.py` | Tabela `logs_sincronizacao` (auditoria de consumo da cota Sienge e rastreamento de erros) |
| `__init__.py` | Registro central de todos os models para autogenerate do Alembic |

---

## 3. Índices de Alta Performance (Escala 750+ Condôminos)

1. **`ix_fotos_diario_geral_parcial`:** Índice parcial PostgreSQL (`WHERE unidade_id IS NULL AND publicado = true`) sobre `(diario_id, ordem)`. Acelera o carregamento do feed geral do edifício ignorando fotos privadas de apartamentos e fotos em quarentena.
2. **`ix_fotos_diario_unidade_parcial`:** Índice parcial PostgreSQL (`WHERE unidade_id IS NOT NULL`) sobre `(unidade_id, status, publicado)`. Garante resposta sub-milissegundo na aba *"Minha Unidade"*.
3. **`ix_diarios_obra_obra_id_data`:** Índice composto em `(obra_id, data)` para paginação cronológica instantânea.

---

## 4. Receitas de Manutenção (Alembic)

### Adicionar uma coluna
1. Adicione o campo no model correspondente em `app/models/`.
2. Gere e aplique a migração:
   ```powershell
   .\.venv\Scripts\alembic.exe revision --autogenerate -m "descricao_da_mudanca"
   .\.venv\Scripts\alembic.exe upgrade head
   ```

### Promover um dado do `dados_sienge` (`JSONB`) para coluna
Crie a coluna e, na mesma migração, popule a partir do payload bruto já salvo sem precisar reconsultar o Sienge:
```python
op.execute("UPDATE obras SET area_construida_m2 = (dados_sienge->>'builtArea')::numeric")
```

### Desfazer a última migração
```powershell
.\.venv\Scripts\alembic.exe downgrade -1
```
