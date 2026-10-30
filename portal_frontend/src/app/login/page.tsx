"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, KeyRound, Loader2 } from "lucide-react";
import { autenticarPorCpf, formatarCpfMascara } from "@/lib/api";
import { BenedettoLogo } from "@/components/BenedettoLogo";

export default function LoginPage() {
  const router = useRouter();
  const [cpf, setCpf] = useState("");
  const [senha, setSenha] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      await autenticarPorCpf(cpf, senha);
      router.push("/");
    } catch (err) {
      setErro(
        err instanceof Error
          ? err.message
          : "Não foi possível conectar ao servidor. Verifique se a API está ativa."
      );
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="relative min-h-screen bg-benedetto-dark text-white flex flex-col justify-between p-6 sm:p-10 overflow-hidden">
      {/* Textura Arquitetônica Canelada Sutil de Fundo (inspirada no vidro canelado da marca) */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(90deg, #FFFFFF 0px, #FFFFFF 1px, transparent 1px, transparent 18px)",
        }}
      />

      {/* Topo Editorial com Marcadores Quadrados da Marca */}
      <header className="relative z-10 max-w-5xl w-full mx-auto flex items-start justify-between text-[11px] font-brand uppercase tracking-[0.25em] text-white/70">
        <div className="space-y-2">
          <span>Empreendimentos</span>
          <div className="w-2 h-2 bg-benedetto-gold" />
        </div>
        <div className="text-right space-y-2 flex flex-col items-end">
          <span>Portal do Condômino</span>
          <div className="w-2 h-2 bg-white/80" />
        </div>
      </header>

      {/* Conteúdo Central: Logotipo Oficial A Ponte + Card Minimalista */}
      <div className="relative z-10 max-w-md w-full mx-auto my-10">
        <div className="flex flex-col items-center text-center mb-10">
          <BenedettoLogo variant="light" size="lg" className="mb-5" />
          <p className="font-display italic text-base sm:text-lg text-white/80 tracking-wide">
            Conexão, evolução e transformação urbana.
          </p>
        </div>

        {/* Moldura Arquitetônica do Formulário */}
        <div className="bg-benedetto-bg text-benedetto-textMain rounded-md border border-benedetto-border shadow-[0_20px_50px_rgba(0,0,0,0.5)] p-6 sm:p-8">
          <div className="mb-6 pb-4 border-b border-benedetto-border flex items-center justify-between">
            <div>
              <p className="font-brand text-[10px] uppercase tracking-[0.25em] text-benedetto-textMuted">
                Acesso Exclusivo
              </p>
              <h1 className="font-display text-xl sm:text-2xl text-benedetto-textMain mt-0.5">
                Espaço do Investidor
              </h1>
            </div>
            <div className="w-2.5 h-2.5 bg-benedetto-gold shrink-0" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="cpf"
                className="block font-brand text-[11px] font-medium uppercase tracking-[0.2em] text-benedetto-textMuted mb-2"
              >
                CPF do Titular
              </label>
              <input
                id="cpf"
                type="text"
                inputMode="numeric"
                autoComplete="username"
                required
                placeholder="000.000.000-00"
                value={cpf}
                onChange={(e) => setCpf(formatarCpfMascara(e.target.value))}
                className="w-full px-4 py-3 rounded-md bg-white border border-benedetto-border text-benedetto-textMain font-medium placeholder:text-benedetto-textMuted/50 focus:outline-none focus:border-benedetto-gold focus:ring-1 focus:ring-benedetto-gold transition"
              />
            </div>

            <div>
              <label
                htmlFor="senha"
                className="block font-brand text-[11px] font-medium uppercase tracking-[0.2em] text-benedetto-textMuted mb-2"
              >
                Credencial de Acesso
              </label>
              <div className="relative">
                <input
                  id="senha"
                  type="password"
                  autoComplete="current-password"
                  required
                  placeholder="••••••••"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  className="w-full px-4 py-3 rounded-md bg-white border border-benedetto-border text-benedetto-textMain font-medium placeholder:text-benedetto-textMuted/50 focus:outline-none focus:border-benedetto-gold focus:ring-1 focus:ring-benedetto-gold transition"
                />
                <KeyRound className="w-4 h-4 text-benedetto-textMuted absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            {erro && (
              <div className="rounded-md bg-red-50/90 border border-red-200 px-3.5 py-3 text-xs font-medium text-red-800">
                {erro}
              </div>
            )}

            <button
              type="submit"
              disabled={carregando}
              className="w-full py-3.5 px-5 rounded-md bg-benedetto-dark hover:bg-benedetto-cardDark text-white font-brand text-xs font-medium uppercase tracking-[0.2em] transition flex items-center justify-center gap-2.5 disabled:opacity-60"
            >
              {carregando ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-benedetto-gold" />
                  <span>Verificando...</span>
                </>
              ) : (
                <>
                  <span>Acessar Meu Empreendimento</span>
                  <ArrowRight className="w-4 h-4 text-benedetto-gold" />
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Rodapé Editorial com Marcadores Quadrados */}
      <footer className="relative z-10 max-w-5xl w-full mx-auto flex items-end justify-between text-[11px] font-brand uppercase tracking-[0.25em] text-white/60">
        <div className="space-y-2">
          <div className="w-2 h-2 bg-white/80" />
          <span>Desenvolvedora</span>
        </div>
        <span>{new Date().getFullYear()}</span>
      </footer>
    </main>
  );
}
