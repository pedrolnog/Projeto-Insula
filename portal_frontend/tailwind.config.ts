import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        benedetto: {
          bg: "#F8F6F2", // Fundo linho/areia (modo claro)
          dark: "#111215", // Preto carvão profundo
          card: "#FFFFFF", // Superfície limpa de cards
          cardDark: "#1A1C20", // Cards no dark mode
          gold: "#C59B63", // Bronze / Dourado solar (acento primário)
          goldHover: "#B08852",
          olive: "#2E3A2F", // Verde oliva arquitetônico
          textMain: "#1E2024", // Títulos e texto principal
          textMuted: "#6B707B", // Legendas e dados secundários
          border: "#E5E0D8", // Bordas finas de plantas baixas
          borderDark: "#2D3036",
        },
      },
      fontFamily: {
        display: ["var(--font-playfair)", "serif"], // Títulos editoriais
        sans: ["var(--font-jakarta)", "sans-serif"], // UI e leitura
        brand: ["var(--font-montserrat)", "sans-serif"], // Nomes de projetos em caixa alta
      },
    },
  },
  plugins: [],
};

export default config;
