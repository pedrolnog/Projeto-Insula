---
id: 11.09 Autenticação e Gestão de Usuários
aliases:
  - Autenticação e Usuários
  - Gestão de Perfis CRUD
tags:
  - tipo/projeto
  - projeto/app
  - seguranca
  - autenticacao
  - jwt
  - crud
  - cli
status: ativo
modulo: App & Portal
sistema: Sienge ERP & Portal do Condômino
upstream:
  - "[[11.01 App - Portal do Condômino]]"
---

# 11.09 Autenticação, Perfis & Gestão de Usuários (CRUD)

> Políticas de credenciais, fluxo de login via CPF e JWT, manual completo do utilitário CLI e endpoints administrativos.

---

## 1. Mecanismo de Autenticação e Perfis

O sistema autentica usuários via **CPF** (normalizado internamente para apenas dígitos numéricos) e senha com hash seguro **Bcrypt/Argon2**.

### 1.1 Perfis de Acesso:
1. **Administrador (`admin`):**
   * Acesso irrestrito a **100% das obras** do sistema automaticamente.
   * **Não necessita de vínculo manual** na tabela associativa `usuarios_obras`.
   * Acesso liberado ao painel de quarentena de fotos (`/api/v1/admin/fotos-quarentena`), curadoria e sincronização manual.
2. **Condômino (`condomino`):**
   * Enxerga apenas as obras cadastradas em `usuarios_obras`.
   * **Multi-Obra:** Se possuir cotas em mais de um empreendimento, o aplicativo renderiza seletor no topo.
   * Enxerga apenas as unidades cadastradas em `usuarios_unidades`.

> [!CAUTION]
> ### Segurança em Produção (`SIENGE_USE_MOCK=false`)
> * Usuários fictícios de demonstração (`00000000000`, `11122233344`, etc.) são **estritamente proibidos e desativados** em ambiente de produção com dados reais.
> * A rotina de seed é ignorada automaticamente quando `SIENGE_USE_MOCK=false`.
> * Novos administradores e condôminos devem ser gerados via script CLI `scripts/criar_usuario.py` ou via API administrativa.

---

## 2. Utilitário CLI no Terminal (`scripts/criar_usuario.py`)

O script oferece controle administrativo completo via linha de comando no terminal:

```powershell
cd C:\Users\pedro\Desktop\Trabalho\Benedetto\BenedettoApp\portal_backend
```

### Comandos Rápidos:

* **1. Listar todos os usuários cadastrados:**
  ```powershell
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --listar
  ```
* **2. Listar obras disponíveis e seus IDs:**
  ```powershell
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --listar-obras
  ```
* **3. Ver detalhes completos por CPF ou ID:**
  ```powershell
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --ver 09135315458
  ```
* **4. Criar Administrador:**
  ```powershell
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --cpf 09135315458 --nome "Pedro Lucas" --senha "sua_senha" --perfil admin
  ```
* **5. Criar Condômino vinculado a múltiplas obras:**
  ```powershell
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --cpf 98765432100 --nome "Ana Carolina" --senha "benedetto123" --perfil condomino --obras 128 129
  ```
* **6. Adicionar ou remover obras de um usuário existente:**
  ```powershell
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --cpf 98765432100 --adicionar-obras 130
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --cpf 98765432100 --remover-obras 129
  ```
* **7. Atualizar dados cadastrais:**
  ```powershell
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --cpf 98765432100 --nome "Ana Carolina Silva" --ativo true
  ```
* **8. Ajustar percentual de evolução física geral ou fase da obra:**
  ```powershell
  # Define a evolução física geral para 14.50%
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --definir-obra-percentual 128 14.5

  # Vira a chave para a fase de reformas das unidades (Ponto X)
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --definir-obra-fase 128 reformas_unidades
  ```
* **9. Apagar usuário permanentemente:**
  ```powershell
  .\.venv\Scripts\python.exe scripts/criar_usuario.py --apagar 98765432100
  ```
* **10. Menu Interativo (terminal):**
  ```powershell
  .\.venv\Scripts\python.exe scripts/criar_usuario.py
  ```
  *(A opção 7 permite ajustar percentual e fase de qualquer obra com menu guiado).*

---

## 3. API REST Administrativa (`/api/v1/admin/usuarios` e `/api/v1/admin/obras`)

Todas as rotas exigem perfil `ADMIN` (`Authorization: Bearer <TOKEN_ADMIN>`).

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| **`GET`** | `/api/v1/admin/usuarios` | Lista usuários paginados com filtros (`perfil`, `busca`). |
| **`GET`** | `/api/v1/admin/usuarios/{id}` | Retorna dados completos e IDs de obras/unidades vinculadas. |
| **`POST`** | `/api/v1/admin/usuarios` | Cadastra novo usuário (`admin` ou `condomino`). |
| **`PATCH`** | `/api/v1/admin/usuarios/{id}` | Atualização parcial (nome, senha, status ativo, obras). |
| **`DELETE`** | `/api/v1/admin/usuarios/{id}` | Exclusão física com trava anti-lockout. |
| **`PATCH`** | `/api/v1/admin/obras/{id}` | Atualiza percentual de evolução física geral (`percentual_concluido`), fase e situação da obra. |

### Exemplo de Criação de Condômino (`POST /api/v1/admin/usuarios`):
```json
{
  "cpf": "123.456.789-00",
  "nome": "Marina Oliveira",
  "senha": "senhaForte123",
  "email": "marina@email.com",
  "telefone": "11987654321",
  "perfil": "condomino",
  "obras_ids": [128],
  "unidades_ids": []
}
```

---

## 4. Credenciais Exclusivas do Ambiente Mock (`SIENGE_USE_MOCK=true`)

Exclusivas para desenvolvimento offline e testes:

| Perfil | CPF | Senha |
| :--- | :--- | :--- |
| **Administrador Mock** | `000.000.000-00` | `admin123` |
| **Condômino Demo (João)** | `111.222.333-44` | `benedetto123` |
| **Condômino Vizinho (Carlos)** | `222.333.444-55` | `benedetto123` |

---

## 5. Conformidade com a LGPD (Lei nº 13.709/2018) & Proteção de Dados

A arquitetura do Portal foi desenhada para blindar dados pessoais e patrimoniais sensíveis contra qualquer tipo de vazamento ou acesso indevido.

### 5.1 Os 5 Pilares de Proteção LGPD no Portal:

1. **Prevenção contra Vazamento Cruzado (Multi-Tenancy Estrito):**
   * Nenhum condômino tem acesso à lista de outros proprietários, CPFs, contatos ou investimentos.
   * Na visualização coletiva do edifício (`/minha-obra/diarios`), o SQL filtra obrigatoriamente `unidade_id IS NULL`, impedindo que fotos de reformas privadas vazem no feed geral.
   * Na rota da unidade (`/minha-obra/unidades/{unidade_id}`), a API valida o vínculo em `usuarios_unidades`. Se outro condômino tentar acessar a unidade do vizinho alterando o ID da URL, a API retorna **`HTTP 403 Forbidden`**.

2. **Base Legal Adequada — Execução de Contrato (Art. 7º, V):**
   * O tratamento de dados decorre da obrigação contratual da construtora de prestar contas da execução física do empreendimento adquirido.
   * Não depende de consentimento frágil revogável, mas exige **transparência**.
   * **Termo de Privacidade no 1º Login:** O banco de dados armazena o timestamp exato do aceite em `usuarios.termo_privacidade_aceito_em`. O condômino visualiza e aceita os termos logo no primeiro acesso ao sistema (`POST /api/v1/auth/aceitar-termo-privacidade`).

3. **Proteção do CPF & Autenticação:**
   * **Rate Limiting no Login:** A rota `/api/v1/auth/login` utiliza *Sliding Window* por IP (com suporte a cabeçalhos `CF-Connecting-IP` da Cloudflare e `X-Forwarded-For`), bloqueando tentativas de força bruta.
   * **Mascaramento em Logs do Servidor:** A função `mascarar_cpf()` sanitiza todo CPF registrado em logs (`***.456.789-**`), impedindo vazamento de credenciais nos logs do servidor ou do terminal.
   * **Hash Criptográfico Forte:** Senhas protegidas com Bcrypt (salt dinâmico com fator 12) rodando em threadpool dedicado.

4. **Direito de Imagem no Canteiro & Ativação da Quarentena (Apenas após o Ponto X):**
   * **Fase Estrutural Geral (`estrutural_geral`) — Fluxo 100% Automático:** Não há curadoria manual no dia a dia. 100% das fotos do canteiro são publicadas diretamente e alimentam o feed coletivo do edifício sem intervenção humana. A recomendação técnica para a equipe de engenharia é focar no avanço técnico da edificação (fundação, ferragem, lajes, concretagem, alvenaria, fachada), evitando primeiros planos em operários individuais sem autorização formal.
   * **Após o Ponto X (`reformas_unidades` e `entrega`) — Ativação da Quarentena:** A curadoria e moderação de fotos só entra em ação a partir do Ponto X. Nesse estágio de acabamentos internos, fotos que chegam do Sienge sem tag clara de unidade são retidas em quarentena (`publicado = False`) para validação rápida do engenheiro, prevenindo o risco de vazamento de reformas particulares no feed geral.

5. **Ciclo de Vida do Dado (Venda de Ágio, Cessão de Direitos ou Distrato):**
   * Caso o cliente venda sua unidade antes da entrega, o administrador desvincula a unidade via `scripts/criar_usuario.py` ou via API administrativa.
   * O ex-condômino perde o acesso de imediato aos diários e fotos daquela unidade.
   * Em caso de distrato total, o perfil é inativado (`ativo = False`), impedindo login e preservando os registros contábeis/fiscais exigidos pelo Código Civil.

---

## 6. Conexões e Links Relacionados
* **Nota Mestre:** [[11.01 App - Portal do Condômino]]
* **Regras do Ponto X & Multi-Tenancy:** [[11.02 Regras de Negócio e Multi-tenancy (Ponto X)]]
* **Setup do Ambiente:** [[11.08 Onboarding e Execução do Ambiente]]
* **Endpoints de Leitura:** [[11.06 Fluxo de Leitura e Endpoints do Condômino]]
* **Modelagem e Índices:** [[11.12 Modelagem de Dados Relacional e Otimizações SQL]]
* **Conformidade com a LGPD:** [[11.14 Conformidade com a LGPD e Segurança de Dados]]
