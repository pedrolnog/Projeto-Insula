"use client";

import { useState } from "react";
import {
  AlertTriangle,
  Camera,
  Check,
  ChevronDown,
  ChevronUp,
  Clock,
  CloudRain,
  HardHat,
  MapPin,
} from "lucide-react";
import {
  type DiarioObra,
  type FotoDiario,
  formatarDataBr,
  resolverUrlMidia,
} from "@/lib/api";

interface DiarioCardProps {
  diario: DiarioObra;
  aoAbrirFoto: (fotos: FotoDiario[], indice: number) => void;
  expandidoInicialmente?: boolean;
}

export function DiarioCard({
  diario,
  aoAbrirFoto,
  expandidoInicialmente = true,
}: DiarioCardProps) {
  const [mostrarTodasTarefas, setMostrarTodasTarefas] = useState(
    expandidoInicialmente
  );

  const tarefasVisiveis = mostrarTodasTarefas
    ? diario.tarefas
    : diario.tarefas.slice(0, 3);

  const chuvaMm =
    diario.indice_pluviometrico !== null &&
    diario.indice_pluviometrico !== undefined
      ? Number(diario.indice_pluviometrico)
      : null;

  return (
    <article className="bg-benedetto-card rounded-md border border-benedetto-border shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] overflow-hidden transition">
      {/* Cabeçalho Editorial do Diário */}
      <div className="p-5 sm:p-6 border-b border-benedetto-border flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-md bg-benedetto-dark text-white flex flex-col items-center justify-center shrink-0 border border-benedetto-borderDark">
            <div className="w-2 h-2 bg-benedetto-gold" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="font-brand text-[10px] uppercase tracking-[0.25em] text-benedetto-gold font-semibold">
                Relatório Técnico
              </span>
              {diario.dia_semana && (
                <span className="text-[11px] font-brand uppercase tracking-widest px-2 py-0.5 rounded-sm bg-benedetto-bg text-benedetto-textMuted border border-benedetto-border">
                  {diario.dia_semana}
                </span>
              )}
            </div>
            <h3 className="font-display text-xl sm:text-2xl text-benedetto-textMain mt-0.5">
              {formatarDataBr(diario.data)}
            </h3>
            {diario.responsavel && (
              <p className="text-xs text-benedetto-textMuted flex items-center gap-1.5 mt-1">
                <HardHat className="w-3.5 h-3.5 text-benedetto-gold" />
                <span>Engenharia Responsável:</span>
                <strong className="font-medium text-benedetto-textMain">
                  {diario.responsavel}
                </strong>
              </p>
            )}
          </div>
        </div>

        {/* Badges Sutis */}
        <div className="flex items-center gap-2 flex-wrap">
          {chuvaMm !== null && chuvaMm > 0 && (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-brand uppercase tracking-wider px-2.5 py-1 rounded-sm bg-benedetto-bg text-benedetto-textMain border border-benedetto-border">
              <CloudRain className="w-3.5 h-3.5 text-benedetto-gold" />
              {chuvaMm} mm
            </span>
          )}
          {diario.fotos.length > 0 && (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-brand uppercase tracking-wider px-2.5 py-1 rounded-sm bg-amber-50/70 text-amber-900 border border-amber-200/60">
              <Camera className="w-3.5 h-3.5 text-benedetto-gold" />
              {diario.fotos.length}{" "}
              {diario.fotos.length === 1 ? "registro" : "registros"}
            </span>
          )}
        </div>
      </div>

      <div className="p-5 sm:p-6 space-y-6">
        {/* Parecer / Observações do Dia */}
        {diario.observacoes && (
          <div className="bg-benedetto-bg rounded-md p-4 border-l-2 border-benedetto-gold text-sm text-benedetto-textMain leading-relaxed">
            {diario.observacoes}
          </div>
        )}

        {/* Turnos de Canteiro */}
        {diario.turnos && diario.turnos.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {diario.turnos.map((turno, idx) => (
              <div
                key={idx}
                className="inline-flex items-center gap-1.5 text-xs bg-benedetto-bg text-benedetto-textMain px-3 py-1.5 rounded-sm border border-benedetto-border"
              >
                <Clock className="w-3.5 h-3.5 text-benedetto-gold" />
                <span className="font-medium">
                  {turno.descricao || "Turno"}:
                </span>
                {turno.inicio && turno.fim && (
                  <span className="text-benedetto-textMuted">
                    {turno.inicio}–{turno.fim}
                  </span>
                )}
                {turno.clima && (
                  <span className="text-benedetto-textMuted">
                    ({turno.clima})
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Atividades Executadas (Planta Baixa / Caderno de Engenharia) */}
        {diario.tarefas.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-brand text-[11px] font-medium uppercase tracking-[0.2em] text-benedetto-textMuted flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-benedetto-gold inline-block" />
                Execução Física do Dia ({diario.tarefas.length})
              </h4>
            </div>

            <ul className="divide-y divide-benedetto-border border border-benedetto-border rounded-md overflow-hidden">
              {tarefasVisiveis.map((tarefa) => {
                const qtd =
                  tarefa.quantidade !== null && tarefa.quantidade !== undefined
                    ? Number(tarefa.quantidade)
                    : null;
                return (
                  <li
                    key={tarefa.id}
                    className="p-3.5 sm:px-4 bg-white hover:bg-benedetto-bg/50 transition flex items-start justify-between gap-3"
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <Check className="w-4 h-4 text-benedetto-gold shrink-0 mt-0.5" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-benedetto-textMain break-words">
                          {tarefa.descricao || "Serviço executado em obra"}
                        </p>
                        {tarefa.observacoes && (
                          <p className="text-xs text-benedetto-textMuted mt-0.5">
                            {tarefa.observacoes}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {qtd !== null && (
                        <span className="text-xs font-medium bg-benedetto-bg text-benedetto-textMain px-2.5 py-1 rounded-sm border border-benedetto-border">
                          {qtd.toLocaleString("pt-BR")}{" "}
                          {tarefa.unidade_medida || ""}
                        </span>
                      )}
                      <span
                        className={`text-[10px] font-brand uppercase tracking-widest px-2 py-0.5 rounded-sm border ${
                          tarefa.tipo === "planejada"
                            ? "bg-benedetto-bg text-benedetto-olive border-benedetto-border"
                            : "bg-amber-50/70 text-amber-900 border-amber-200/60"
                        }`}
                      >
                        {tarefa.tipo === "planejada" ? "Cronograma" : "Complementar"}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>

            {diario.tarefas.length > 3 && (
              <button
                type="button"
                onClick={() => setMostrarTodasTarefas((v) => !v)}
                className="mt-3 font-brand text-[11px] uppercase tracking-[0.18em] text-benedetto-textMain hover:text-benedetto-gold inline-flex items-center gap-1.5 transition"
              >
                {mostrarTodasTarefas ? (
                  <>
                    Recolher lista <ChevronUp className="w-3.5 h-3.5" />
                  </>
                ) : (
                  <>
                    Expandir todas as {diario.tarefas.length} atividades{" "}
                    <ChevronDown className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            )}
          </div>
        )}

        {/* Ocorrências Relevantes / Nota de Canteiro */}
        {diario.ocorrencias && diario.ocorrencias.length > 0 ? (
          <div className="space-y-2">
            {diario.ocorrencias.map((oc, i) => {
              const textoNota = oc.descricao?.trim() || "";
              return (
                <div
                  key={i}
                  className="flex items-start gap-2.5 text-xs bg-amber-50/60 text-amber-900 border border-amber-200/60 rounded-md p-3.5"
                >
                  <AlertTriangle className="w-4 h-4 text-benedetto-gold shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">
                      {oc.tipo || "Nota de Canteiro"}:{" "}
                    </span>
                    {textoNota ? (
                      <span>{textoNota}</span>
                    ) : (
                      <em className="italic text-amber-900/75">
                        não há nota de canteiro
                      </em>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex items-start gap-2.5 text-xs bg-amber-50/60 text-amber-900 border border-amber-200/60 rounded-md p-3.5">
            <AlertTriangle className="w-4 h-4 text-benedetto-gold shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Nota de Canteiro: </span>
              <em className="italic text-amber-900/75">
                não há nota de canteiro
              </em>
            </div>
          </div>
        )}

        {/* Galeria Editorial de Fotos (Proporção 4:5 com Zoom Suave) */}
        {diario.fotos.length > 0 && (
          <div>
            <h4 className="font-brand text-[11px] font-medium uppercase tracking-[0.2em] text-benedetto-textMuted flex items-center gap-2 mb-3">
              <span className="w-1.5 h-1.5 bg-benedetto-gold inline-block" />
              Registros Fotográficos ({diario.fotos.length})
            </h4>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {diario.fotos.map((foto, index) => (
                <button
                  key={foto.id}
                  type="button"
                  onClick={() => aoAbrirFoto(diario.fotos, index)}
                  className="group relative aspect-[4/5] rounded-md overflow-hidden bg-benedetto-dark border border-benedetto-border focus:outline-none focus:ring-1 focus:ring-benedetto-gold text-left"
                >
                  <img
                    src={resolverUrlMidia(foto.url)}
                    alt={foto.descricao || "Foto do diário de obra"}
                    loading="lazy"
                    className="w-full h-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
                  />
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-benedetto-dark/90 via-benedetto-dark/40 to-transparent p-3 pt-8">
                    <p className="text-xs font-medium text-white line-clamp-1">
                      {foto.descricao || "Ampliar registro"}
                    </p>
                    {foto.local && (
                      <p className="font-brand text-[10px] uppercase tracking-[0.15em] text-benedetto-gold flex items-center gap-1 line-clamp-1 mt-1">
                        <MapPin className="w-3 h-3 shrink-0" />
                        {foto.local}
                      </p>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </article>
  );
}
