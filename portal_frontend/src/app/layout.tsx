import type { Metadata, Viewport } from "next";
import {
  Montserrat,
  Playfair_Display,
  Plus_Jakarta_Sans,
} from "next/font/google";
import "./globals.css";

const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-playfair",
  display: "swap",
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-jakarta",
  display: "swap",
});

const montserrat = Montserrat({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-montserrat",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BENEDETTO | Portal do Condômino",
  description:
    "Acompanhamento arquitetônico, evolução física, diários de obra e registros fotográficos do seu empreendimento Benedetto.",
  manifest: "/manifest.json",
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "BENEDETTO",
  },
};

export const viewport: Viewport = {
  themeColor: "#111215",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="pt-BR"
      className={`${playfair.variable} ${jakarta.variable} ${montserrat.variable}`}
    >
      <body className="min-h-screen flex flex-col bg-benedetto-bg text-benedetto-textMain font-sans">
        {children}
      </body>
    </html>
  );
}
