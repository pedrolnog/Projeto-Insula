---
id: 11.13 Frontend, PWA e Design System Editorial
aliases:
  - Frontend e Design System
  - PWA e Interface Editorial
  - portal_frontend
tags:
  - tipo/projeto
  - projeto/app
  - frontend
  - nextjs
  - react
  - tailwind
  - pwa
  - ui-ux
  - design-system
status: ativo
modulo: App & Portal
sistema: Portal do Condômino
upstream:
  - "[[11.01 App - Portal do Condômino]]"
---

# 11.13 Frontend, PWA & Design System Editorial

> Arquitetura da aplicação cliente `portal_frontend` em Next.js 15, especificações do Design System Editorial Benedetto, paleta de cores, tipografia, componentes essenciais, configuração PWA e proxy transparente.

---

## 1. Visão Geral da Camada de Apresentação

O `portal_frontend` é uma aplicação web **Mobile-First / PWA** desenvolvida em **Next.js 15 (App Router) + React + TypeScript + Tailwind CSS**, concebida para traduzir a linguagem arquitetônica e o padrão de acabamento da Construtora Benedetto para uma experiência digital editorial e minimalista.

```text
portal_frontend/
├── public/
│   ├── icon.svg                # Logotipo vetorial para instalação PWA
│   └── manifest.json           # Web App Manifest (standalone, tema #111215)
├── src/
│   ├── app/
│   │   ├── login/page.tsx      # Tela de Login Editorial (textura canelada + máscara CPF)
│   │   ├── globals.css         # Estilos globais e diretivas Tailwind
│   │   ├── layout.tsx          # Carregamento de fontes Google e metadados PWA
│   │   └── page.tsx            # Dashboard Principal (Obra, Abas, Ponto X, Curadoria Admin e Modal LGPD)
│   ├── components/
│   │   ├── BenedettoLogo.tsx   # Logotipo SVG oficial "A Ponte" (variantes light e dark)
│   │   ├── DiarioCard.tsx      # Card editorial de Diário (clima, turnos, tarefas, ocorrências e fotos 4:5)
│   │   └── LightboxModal.tsx   # Visualizador de fotos em tela cheia com teclado (Setas e ESC)
│   └── lib/
│       └── api.ts              # Cliente HTTP tipado, gestão de sessão e formatadores BR
├── next.config.ts              # Rewrites automáticos (/api/v1/* e /media/* -> Backend 8000)
└── tailwind.config.ts          # Tokens de cores e tipografia do Design System
```

---

## 2. Design System Editorial Benedetto

### 2.1 Paleta de Cores Oficial (`tailwind.config.ts`)

| Token Tailwind | HEX | Função Visual na Interface |
| :--- | :---: | :--- |
| `benedetto-bg` | `#F8F6F2` | Fundo principal linho/areia natural (evita o branco puro estéril) |
| `benedetto-dark` | `#111215` | Preto carvão profundo (Header, tela de login, rodapé de cards e Lightbox) |
| `benedetto-card` | `#FFFFFF` | Superfície limpa dos cards de obras e diários de obra |
| `benedetto-cardDark` | `#1A1C20` | Superfície secundária escura para botões e painéis |
| `benedetto-gold` | `#C59B63` | Bronze / Dourado solar (barras de progresso, marcadores e destaques) |
| `benedetto-goldHover` | `#B08852` | Estado *hover* de botões e links dourados |
| `benedetto-olive` | `#2E3A2F` | Verde oliva arquitetônico (badges de fase Ponto X e tarefas planejadas) |
| `benedetto-textMain` | `#1E2024` | Grafite escuro para leitura principal |
| `benedetto-textMuted` | `#6B707B` | Cinza concreto para datas, legendas e dados secundários |
| `benedetto-border` | `#E5E0D8` | Linhas finas estruturais estilo planta baixa (tema claro) |
| `benedetto-borderDark` | `#2D3036` | Divisores sutis no tema escuro |

### 2.2 Tipografia Editorial (`src/app/layout.tsx`)
* **`font-brand` (`Montserrat`):** Aplicada em caixa alta com espaçamento expandido (`uppercase tracking-[0.25em]`) para nomes de empreendimentos (*RIVUS*, *VIRTUS*, *JARDIM CASALTA*, *LOFT ORLA*, *VITAE*), abas do app e selos de engenharia.
* **`font-display` (`Playfair Display`):** Serifa editorial de alto contraste usada em números de evolução física (`14,5%`), datas de diários e títulos de modais.
* **`font-sans` (`Plus Jakarta Sans`):** Tipografia geométrica contemporânea para corpo de texto, pareceres de engenharia, listas de tarefas, inputs e tabelas.

---

## 3. Componentes Principais da Interface

### 3.1 `BenedettoLogo.tsx`
Renderização vetorial SVG do símbolo proprietário "A Ponte" e da tipografia da marca Benedetto, suportando alternância de temas (`variant="light"` e `variant="dark"`).

### 3.2 `DiarioCard.tsx`
Card editorial que consolida os dados do canteiro de obras:
* **Cabeçalho:** Data por extenso, dia da semana, responsável técnico e temperatura/índice pluviométrico em `mm`.
* **Corpo:** Turnos de trabalho (manhã/tarde/noite), tarefas planejadas e avulsas executadas, e ocorrências climáticas ou operacionais.
* **Galeria Fotográfica:** Imagens formatadas na proporção editorial vertical `4:5`, otimizadas para telas de smartphones.

### 3.3 `LightboxModal.tsx`
Visualizador de fotos em alta definição com fundo translúcido escuro:
* Suporte nativo à navegação por gestos de toque (swipe) e teclado (setas esquerda/direita e `ESC` para fechar).
* Exibição de metadados da imagem (número do anexo e data de registro).

---

## 4. Configuração PWA (Progressive Web App)

* **`manifest.json`:** Define o comportamento como aplicativo nativo (`display: standalone`), orientação preferencial vertical (`portrait`), cor de fundo `#111215` e nome do aplicativo ("Benedetto Condômino").
* **Ícone Vetorial (`icon.svg`):** Marca vetorial escalável para tela inicial em dispositivos iOS e Android.

---

## 5. Arquitetura de Proxy e Gestão de Sessão

### 5.1 Proxy Transparente via Rewrites (`next.config.ts`)
Para simplificar o desenvolvimento e a infraestrutura, o servidor Node.js do Next.js atua como *Reverse Proxy*:
```typescript
async rewrites() {
  const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
  return [
    { source: "/api/v1/:path*", destination: `${backendUrl}/api/v1/:path*` },
    { source: "/media/:path*", destination: `${backendUrl}/media/:path*` },
  ];
}
```
* **Benefícios:** Elimina problemas de CORS entre portas diferentes no ambiente local e viabiliza expor unicamente a porta `3000` via Cloudflare Quick Tunnel.

### 5.2 Persistência e Ciclo de Sessão (`src/lib/api.ts`)
* O token JWT de acesso e os dados resumidos do perfil são armazenados no `localStorage` sob as chaves:
  * `benedetto_portal_token`
  * `benedetto_portal_user`
* **Auto-Logout em `HTTP 401 Unauthorized`:** Qualquer requisição à API (exceto na tela de `/login`) que receba código `401` limpa o `localStorage` e redireciona automaticamente o navegador para `/login`.

---

## 6. Conexões e Links Relacionados
* **Nota Mestre de Arquitetura:** [[11.01 App - Portal do Condômino]]
* **Estrutura de Pastas Geral:** [[11.03 Estrutura de Código e Camadas do Backend]]
* **Endpoints Consumidos:** [[11.06 Fluxo de Leitura e Endpoints do Condômino]]
* **Guia de Execução (Terminal 2):** [[11.08 Onboarding e Execução do Ambiente]]
* **Segurança e LGPD:** [[11.14 Conformidade com a LGPD e Segurança de Dados]]
