"use client";

import { useEffect } from "react";
import { ChevronLeft, ChevronRight, MapPin, X } from "lucide-react";
import { type FotoDiario, resolverUrlMidia } from "@/lib/api";

interface LightboxModalProps {
  fotos: FotoDiario[];
  indiceAtual: number;
  aoFechar: () => void;
  aoMudarIndice: (novoIndice: number) => void;
}

export function LightboxModal({
  fotos,
  indiceAtual,
  aoFechar,
  aoMudarIndice,
}: LightboxModalProps) {
  const foto = fotos[indiceAtual];

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") aoFechar();
      if (e.key === "ArrowLeft" && indiceAtual > 0) {
        aoMudarIndice(indiceAtual - 1);
      }
      if (e.key === "ArrowRight" && indiceAtual < fotos.length - 1) {
        aoMudarIndice(indiceAtual + 1);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [indiceAtual, fotos.length, aoFechar, aoMudarIndice]);

  if (!foto) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-benedetto-dark/98 backdrop-blur-md flex flex-col justify-between p-4 sm:p-8 select-none"
      onClick={aoFechar}
    >
      {/* Topo Editorial do Lightbox */}
      <div
        className="flex items-center justify-between text-white max-w-5xl w-full mx-auto pb-3 border-b border-benedetto-borderDark"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 bg-benedetto-gold" />
          <span className="font-brand text-xs uppercase tracking-[0.25em] text-white/80">
            Registro {String(indiceAtual + 1).padStart(2, "0")} /{" "}
            {String(fotos.length).padStart(2, "0")}
          </span>
        </div>
        <button
          type="button"
          onClick={aoFechar}
          className="p-2 rounded-md bg-benedetto-cardDark hover:bg-white/10 border border-benedetto-borderDark text-white transition"
          aria-label="Fechar galeria"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Área Central da Imagem */}
      <div
        className="relative flex-1 flex items-center justify-center my-4 max-w-5xl w-full mx-auto overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {indiceAtual > 0 && (
          <button
            type="button"
            onClick={() => aoMudarIndice(indiceAtual - 1)}
            className="absolute left-2 z-10 p-3 rounded-md bg-benedetto-dark/80 text-white hover:bg-benedetto-gold hover:text-benedetto-dark border border-benedetto-borderDark transition"
            aria-label="Foto anterior"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        )}

        <img
          src={resolverUrlMidia(foto.url)}
          alt={foto.descricao || "Registro fotográfico da obra"}
          className="max-h-[74vh] max-w-full object-contain rounded-md border border-benedetto-borderDark shadow-2xl"
        />

        {indiceAtual < fotos.length - 1 && (
          <button
            type="button"
            onClick={() => aoMudarIndice(indiceAtual + 1)}
            className="absolute right-2 z-10 p-3 rounded-md bg-benedetto-dark/80 text-white hover:bg-benedetto-gold hover:text-benedetto-dark border border-benedetto-borderDark transition"
            aria-label="Próxima foto"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Legenda Inferior Arquitetônica */}
      <div
        className="max-w-3xl w-full mx-auto bg-benedetto-cardDark border border-benedetto-borderDark rounded-md p-4 text-white"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="font-display text-base sm:text-lg text-white">
          {foto.descricao || "Registro fotográfico de evolução da obra"}
        </p>
        {foto.local && (
          <p className="font-brand text-[11px] uppercase tracking-[0.2em] text-benedetto-gold flex items-center gap-1.5 mt-1.5">
            <MapPin className="w-3.5 h-3.5 shrink-0" />
            {foto.local}
          </p>
        )}
      </div>
    </div>
  );
}
