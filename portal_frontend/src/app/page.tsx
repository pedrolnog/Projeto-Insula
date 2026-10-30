"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Camera,
  Check,
  ClipboardList,
  Home,
  Images,
  Loader2,
  LogOut,
  MapPin,
  Pencil,
  RefreshCw,
  ShieldAlert,
  Sliders,
  X,
} from "lucide-react";
import {
  type DiarioObra,
  type FaseObra,
  type FotoDiario,
  type FotoQuarentenaAdmin,
  type MinhaObraResponse,
  type MinhaUnidadeDetalheResponse,
  type StatusReformaUnidade,
  type UsuarioResumo,
  aceitarTermoPrivacidade,
  atualizarObraAdmin,
  buscarDetalheMinhaUnidade,
  buscarMinhaObra,
  classificarFotoQuarentenaAdmin,
  dispararSincronizacaoAdmin,
  formatarDataBr,
  formatarDataHoraBr,
  limparSessao,
  listarDiariosMinhaObra,
  listarFotosQuarentenaAdmin,
  obterTokenSalvo,
  obterUsuarioSalvo,
  resolverUrlMidia,
} from "@/lib/api";
import { BenedettoLogo } from "@/components/BenedettoLogo";
import { DiarioCard } from "@/components/DiarioCard";
import { LightboxModal } from "@/components/LightboxModal";

function traduzirStatusReforma(status: StatusReformaUnidade): {
  rotulo: string;
  classes: string;
} {
  switch (status) {
    case "concluida":
      return {
        rotulo: "Acabamento Concluído",
        classes:
          "bg-emerald-950/60 text-emerald-300 border-emerald-700/50",
      };
    case "em_andamento":
      return {
        rotulo: "Reforma em Execução",
        classes:
          "bg-benedetto-gold/15 text-benedetto-gold border-benedetto-gold/40",
      };
    default:
      return {
        rotulo: "Cronograma Programado",
        classes: "bg-white/5 text-white/70 border-white/15",
      };
  }
}

export default function DashboardCondominoPage() {
  const router = useRouter();

  const [usuario, setUsuario] = useState<UsuarioResumo | null>(null);
  const [obra, setObra] = useState<MinhaObraResponse | null>(null);
  const [obraSelecionadaId, setObraSelecionadaId] = useState<number | null>(
    null
  );
  const [diarios, setDiarios] = useState<DiarioObra[]>([]);
  const [pagina, setPagina] = useState(1);
  const [totalPaginas, setTotalPaginas] = useState(1);

  // Ponto X: Estado da unidade selecionada do condômino
  const [unidadeSelecionadaId, setUnidadeSelecionadaId] = useState<
    number | null
  >(null);
  const [detalheUnidade, setDetalheUnidade] =
    useState<MinhaUnidadeDetalheResponse | null>(null);
  const [carregandoUnidade, setCarregandoUnidade] = useState(false);

  const [abaAtiva, setAbaAtiva] = useState<
    "unidade" | "diarios" | "galeria" | "quarentena"
  >("diarios");
  const [fotosQuarentena, setFotosQuarentena] = useState<FotoQuarentenaAdmin[]>(
    []
  );
  const [classificandoFotoId, setClassificandoFotoId] = useState<number | null>(
    null
  );
  const [carregando, setCarregando] = useState(true);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // Estado para Edição Administrativa da Obra (Percentual de Evolução e Fase)
  const [modalEditarObraAberto, setModalEditarObraAberto] = useState(false);
  const [editPercentual, setEditPercentual] = useState("");
  const [editFase, setEditFase] = useState<FaseObra>("estrutural_geral");
  const [salvandoObra, setSalvandoObra] = useState(false);
  const [erroEditarObra, setErroEditarObra] = useState<string | null>(null);

  // Estado do Lightbox de Fotos
  const [lightboxFotos, setLightboxFotos] = useState<FotoDiario[] | null>(null);
  const [lightboxIndice, setLightboxIndice] = useState(0);

  // Estado para Modal de LGPD / Termo de Privacidade no 1º Login
  const [exibirModalPrivacidade, setExibirModalPrivacidade] = useState(false);
  const [aceitandoTermo, setAceitandoTermo] = useState(false);

  const handleAceitarPrivacidade = async () => {
    try {
      setAceitandoTermo(true);
      const resp = await aceitarTermoPrivacidade();
      if (usuario) {
        const atualizado = {
          ...usuario,
          termo_privacidade_aceito_em: resp.termo_privacidade_aceito_em,
        };
        setUsuario(atualizado);
        if (typeof window !== "undefined") {
          localStorage.setItem(
            "benedetto_portal_user",
            JSON.stringify(atualizado)
          );
        }
      }
      setExibirModalPrivacidade(false);
    } catch (err) {
      console.error("Erro ao aceitar termo:", err);
    } finally {
      setAceitandoTermo(false);
    }
  };

  const carregarUnidadeEspecifica = useCallback(async (idUnidade: number) => {
    setCarregandoUnidade(true);
    try {
      const dadosUnidade = await buscarDetalheMinhaUnidade(idUnidade);
      setDetalheUnidade(dadosUnidade);
      setUnidadeSelecionadaId(idUnidade);
    } catch (err) {
      setErro(
        err instanceof Error
          ? err.message
          : "Não foi possível carregar os detalhes da sua unidade."
      );
    } finally {
      setCarregandoUnidade(false);
    }
  }, []);

  const carregarDadosObra = useCallback(
    async (idObraAlvo?: number | null) => {
      setCarregando(true);
      setErro(null);
      try {
        const [dadosObra, dadosDiarios] = await Promise.all([
          buscarMinhaObra(idObraAlvo),
          listarDiariosMinhaObra({
            obraId: idObraAlvo,
            pagina: 1,
            tamanhoPagina: 10,
          }),
        ]);
        setObra(dadosObra);
        setObraSelecionadaId(dadosObra.id);
        setDiarios(dadosDiarios.itens);
        setPagina(1);
        setTotalPaginas(dadosDiarios.total_paginas);

        const usr = obterUsuarioSalvo();
        if (usr?.perfil === "admin") {
          try {
            const retidas = await listarFotosQuarentenaAdmin(dadosObra.id);
            setFotosQuarentena(retidas);
          } catch {
            setFotosQuarentena([]);
          }
        }

        const possuiUnidades =
          dadosObra.unidades_vinculadas &&
          dadosObra.unidades_vinculadas.length > 0;

        if (possuiUnidades) {
          const primeiraUnidadeId = dadosObra.unidades_vinculadas[0].id;
          await carregarUnidadeEspecifica(primeiraUnidadeId);
          if (
            dadosObra.fase_atual === "reformas_unidades" ||
            dadosObra.fase_atual === "entrega"
          ) {
            setAbaAtiva("unidade");
          } else {
            setAbaAtiva("diarios");
          }
        } else {
          setDetalheUnidade(null);
          setUnidadeSelecionadaId(null);
          setAbaAtiva("diarios");
        }
      } catch (err) {
        setErro(
          err instanceof Error
            ? err.message
            : "Não foi possível carregar os dados da sua obra."
        );
      } finally {
        setCarregando(false);
      }
    },
    [carregarUnidadeEspecifica]
  );

  useEffect(() => {
    const token = obterTokenSalvo();
    if (!token) {
      router.replace("/login");
      return;
    }
    const usr = obterUsuarioSalvo();
    setUsuario(usr);
    if (usr && !usr.termo_privacidade_aceito_em) {
      setExibirModalPrivacidade(true);
    }
    void carregarDadosObra(null);
  }, [router, carregarDadosObra]);

  async function handleCarregarMaisDiarios() {
    if (carregandoMais || pagina >= totalPaginas) return;
    setCarregandoMais(true);
    try {
      const proxima = pagina + 1;
      const resposta = await listarDiariosMinhaObra({
        obraId: obraSelecionadaId,
        pagina: proxima,
        tamanhoPagina: 10,
      });
      setDiarios((atuais) => [...atuais, ...resposta.itens]);
      setPagina(proxima);
      setTotalPaginas(resposta.total_paginas);
    } catch (err) {
      setErro(
        err instanceof Error ? err.message : "Erro ao carregar mais diários."
      );
    } finally {
      setCarregandoMais(false);
    }
  }

  async function handleSincronizarAgora() {
    if (sincronizando) return;
    setSincronizando(true);
    setErro(null);
    try {
      await dispararSincronizacaoAdmin(obraSelecionadaId);
      await carregarDadosObra(obraSelecionadaId);
    } catch (err) {
      setErro(
        err instanceof Error ? err.message : "Falha ao sincronizar com o Sienge."
      );
    } finally {
      setSincronizando(false);
    }
  }

  function handleLogout() {
    limparSessao();
    router.replace("/login");
  }

  async function handleClassificarFoto(
    fotoId: number,
    unidadeId: number | null
  ) {
    setClassificandoFotoId(fotoId);
    setErro(null);
    try {
      await classificarFotoQuarentenaAdmin(fotoId, {
        unidade_id: unidadeId,
        publicado: true,
      });
      await carregarDadosObra(obraSelecionadaId);
    } catch (err) {
      setErro(
        err instanceof Error
          ? err.message
          : "Não foi possível classificar a foto."
      );
    } finally {
      setClassificandoFotoId(null);
    }
  }

  function abrirModalEditarObra() {
    if (!obra) return;
    setEditPercentual(String(obra.percentual_concluido ?? 0));
    setEditFase(obra.fase_atual);
    setErroEditarObra(null);
    setModalEditarObraAberto(true);
  }

  async function handleSalvarEdicaoObra(e: React.FormEvent) {
    e.preventDefault();
    if (!obra) return;
    const num = parseFloat(editPercentual.replace(",", "."));
    if (isNaN(num) || num < 0 || num > 100) {
      setErroEditarObra("Informe um percentual válido entre 0% e 100%.");
      return;
    }
    setSalvandoObra(true);
    setErroEditarObra(null);
    try {
      await atualizarObraAdmin(obra.id, {
        percentual_concluido: num,
        fase_atual: editFase,
      });
      setObra((prev) =>
        prev
          ? {
              ...prev,
              percentual_concluido: num,
              fase_atual: editFase,
            }
          : null
      );
      setModalEditarObraAberto(false);
    } catch (err) {
      setErroEditarObra(
        err instanceof Error
          ? err.message
          : "Erro ao atualizar a evolução da obra."
      );
    } finally {
      setSalvandoObra(false);
    }
  }

  // Galeria consolidada apenas das fotos GERAIS do edifício
  const todasFotosGeraisDaObra = useMemo(() => {
    const lista: Array<{ foto: FotoDiario; dataDiario: string }> = [];
    for (const d of diarios) {
      for (const f of d.fotos) {
        lista.push({ foto: f, dataDiario: d.data });
      }
    }
    return lista;
  }, [diarios]);

  const percentualObraNumero = useMemo(() => {
    if (
      !obra ||
      obra.percentual_concluido === null ||
      obra.percentual_concluido === undefined
    ) {
      return 0;
    }
    const valor = Number(obra.percentual_concluido);
    return Number.isFinite(valor) ? Math.min(100, Math.max(0, valor)) : 0;
  }, [obra]);

  const percentualUnidadeNumero = useMemo(() => {
    if (!detalheUnidade) return 0;
    const valor = Number(detalheUnidade.percentual_reforma);
    return Number.isFinite(valor) ? Math.min(100, Math.max(0, valor)) : 0;
  }, [detalheUnidade]);

  if (carregando) {
    return (
      <div className="min-h-screen bg-benedetto-bg flex flex-col items-center justify-center p-6 text-center">
        <BenedettoLogo variant="dark" size="sm" className="mb-6 opacity-90" />
        <Loader2 className="w-6 h-6 text-benedetto-gold animate-spin mb-3" />
        <p className="font-brand text-[11px] uppercase tracking-[0.25em] text-benedetto-textMuted">
          Carregando caderno de obra...
        </p>
      </div>
    );
  }

  const temUnidadesVinculadas =
    Boolean(obra?.unidades_vinculadas) &&
    (obra?.unidades_vinculadas.length ?? 0) > 0;
  const emFaseDeUnidades =
    obra?.fase_atual === "reformas_unidades" || obra?.fase_atual === "entrega";

  const fotoCapaEditorial =
    obra?.imagem_capa_url || todasFotosGeraisDaObra[0]?.foto.url || null;

  return (
    <div className="min-h-screen bg-benedetto-bg pb-20">
      {/* Top Navbar Arquitetônica Preta Profunda (#111215) */}
      <header className="sticky top-0 z-30 bg-benedetto-dark text-white border-b border-benedetto-borderDark">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 min-w-0">
            <BenedettoLogo variant="light" size="sm" className="shrink-0" />
            <div className="hidden sm:block h-5 w-px bg-benedetto-borderDark" />
            <div className="min-w-0 hidden sm:block">
              <p className="font-brand text-[9px] uppercase tracking-[0.25em] text-benedetto-gold truncate">
                Portal do Condômino
              </p>
              <p className="text-xs font-medium text-white/90 truncate">
                {usuario?.nome || "Investidor"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            {usuario?.perfil === "admin" && (
              <button
                type="button"
                onClick={handleSincronizarAgora}
                disabled={sincronizando}
                className="inline-flex items-center gap-2 font-brand text-[10px] uppercase tracking-[0.18em] px-3.5 py-2 rounded-md bg-benedetto-gold hover:bg-benedetto-goldHover text-benedetto-dark font-semibold transition disabled:opacity-60"
                title="Sincronizar agora com o ERP Sienge"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${
                    sincronizando ? "animate-spin" : ""
                  }`}
                />
                <span className="hidden sm:inline">
                  {sincronizando ? "Sincronizando..." : "Sincronizar Sienge"}
                </span>
              </button>
            )}

            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 font-brand text-[10px] uppercase tracking-[0.2em] px-3 py-2 rounded-md bg-benedetto-cardDark hover:bg-white/10 text-white/90 border border-benedetto-borderDark transition"
              aria-label="Sair da conta"
            >
              <LogOut className="w-3.5 h-3.5 text-benedetto-gold" />
              <span>Sair</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-6 space-y-6">
        {erro && (
          <div className="rounded-md bg-red-50 border border-red-200 p-4 text-xs font-medium text-red-800">
            {erro}
          </div>
        )}

        {/* Seletor de Empreendimentos em Caixa Alta com Tracking Expandido */}
        {obra && obra.obras_vinculadas.length > 1 && (
          <div className="flex items-center gap-2.5 overflow-x-auto pb-1">
            {obra.obras_vinculadas.map((item) => {
              const ativa = item.id === obra.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => void carregarDadosObra(item.id)}
                  className={`px-4 py-2.5 rounded-md font-brand text-[11px] uppercase tracking-[0.25em] whitespace-nowrap transition border ${
                    ativa
                      ? "bg-benedetto-dark text-white border-benedetto-dark"
                      : "bg-benedetto-card text-benedetto-textMain border-benedetto-border hover:border-benedetto-gold"
                  }`}
                >
                  {item.nome}
                </button>
              );
            })}
          </div>
        )}

        {/* Card Principal de Resumo da Obra (Editorial Arquitetônico) */}
        {obra && (
          <section className="bg-benedetto-card rounded-md border border-benedetto-border shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] overflow-hidden">
            {/* Painel Escuro do Empreendimento com Imagem de Capa Sutil */}
            <div className="relative bg-benedetto-dark text-white p-6 sm:p-8 overflow-hidden">
              {fotoCapaEditorial && (
                <img
                  src={resolverUrlMidia(fotoCapaEditorial)}
                  alt={obra.nome}
                  className="pointer-events-none absolute inset-0 w-full h-full object-cover opacity-20 mix-blend-luminosity"
                />
              )}
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-benedetto-dark via-benedetto-dark/85 to-benedetto-dark/60" />

              <div className="relative z-10 flex flex-col sm:flex-row sm:items-end justify-between gap-6">
                <div className="space-y-3">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="w-2 h-2 bg-benedetto-gold inline-block" />
                    <span className="font-brand text-[10px] uppercase tracking-[0.25em] px-2.5 py-0.5 rounded-sm bg-white/5 text-benedetto-gold border border-benedetto-gold/40">
                      {obra.situacao || "Em Execução"}
                    </span>
                    {emFaseDeUnidades && (
                      <span className="font-brand text-[10px] uppercase tracking-[0.2em] px-2.5 py-0.5 rounded-sm bg-benedetto-olive/80 text-white border border-white/15">
                        Fase Ponto X • Acabamentos Internos
                      </span>
                    )}
                  </div>

                  {/* Nome do Empreendimento no padrão RIVUS / VIRTUS / LOFT ORLA */}
                  <h1 className="font-brand font-light text-2xl sm:text-4xl uppercase tracking-[0.25em] text-white leading-tight">
                    {obra.nome}
                  </h1>

                  {(obra.endereco || obra.cidade) && (
                    <p className="text-xs text-white/70 flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-benedetto-gold shrink-0" />
                      <span>
                        {[obra.endereco, obra.cidade, obra.uf]
                          .filter(Boolean)
                          .join(" • ")}
                      </span>
                    </p>
                  )}
                </div>

                {/* Percentual de Evolução Físico Editorial */}
                <div className="sm:text-right shrink-0 border-t sm:border-t-0 pt-4 sm:pt-0 border-benedetto-borderDark flex flex-col sm:items-end justify-center">
                  <div className="flex items-center gap-2">
                    <span className="font-brand text-[10px] uppercase tracking-[0.25em] text-white/60 block">
                      Evolução Física Geral
                    </span>
                    {usuario?.perfil === "admin" && (
                      <button
                        type="button"
                        onClick={abrirModalEditarObra}
                        className="text-[9px] font-brand uppercase tracking-[0.15em] px-2 py-0.5 rounded bg-white/10 hover:bg-benedetto-gold hover:text-benedetto-dark text-white/80 transition flex items-center gap-1 cursor-pointer"
                        title="Ajustar percentual e fase da obra"
                      >
                        <Pencil className="w-2.5 h-2.5" />
                        <span>Ajustar</span>
                      </button>
                    )}
                  </div>
                  <span className="font-display text-3xl sm:text-4xl text-benedetto-gold mt-0.5">
                    {percentualObraNumero.toFixed(1).replace(".", ",")}%
                  </span>
                </div>
              </div>

              {/* Barra de Progresso Fina e Elegante em Ouro Queimado */}
              <div className="relative z-10 mt-6">
                <div className="w-full h-1.5 bg-white/10 rounded-none overflow-hidden">
                  <div
                    className="h-full bg-benedetto-gold transition-all duration-700"
                    style={{ width: `${percentualObraNumero}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Indicadores Técnicos de Planta Baixa */}
            <div className="grid grid-cols-3 divide-x divide-benedetto-border border-b border-benedetto-border bg-benedetto-card">
              <div className="p-4 text-center">
                <p className="font-brand text-[10px] uppercase tracking-[0.2em] text-benedetto-textMuted">
                  Unidades Vinculadas
                </p>
                <p className="font-display text-xl sm:text-2xl text-benedetto-textMain mt-1">
                  {String(obra.unidades_vinculadas.length).padStart(2, "0")}
                </p>
              </div>

              <div className="p-4 text-center">
                <p className="font-brand text-[10px] uppercase tracking-[0.2em] text-benedetto-textMuted">
                  Diários Emitidos
                </p>
                <p className="font-display text-xl sm:text-2xl text-benedetto-textMain mt-1">
                  {String(obra.total_diarios).padStart(2, "0")}
                </p>
              </div>

              <div className="p-4 text-center">
                <p className="font-brand text-[10px] uppercase tracking-[0.2em] text-benedetto-textMuted">
                  Última Atualização
                </p>
                <p className="font-display text-base sm:text-lg text-benedetto-textMain mt-1.5">
                  {formatarDataBr(obra.ultimo_diario_data)}
                </p>
              </div>
            </div>

            {/* Rodapé Técnico do Card */}
            <div className="px-5 py-3 bg-benedetto-bg flex flex-wrap items-center justify-between gap-2 text-[11px] text-benedetto-textMuted">
              <span className="font-brand uppercase tracking-[0.18em] flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-benedetto-olive inline-block" />
                Relatório Oficial de Engenharia Benedetto
              </span>
              {obra.sincronizado_em && (
                <span>
                  Sincronizado em {formatarDataHoraBr(obra.sincronizado_em)}
                </span>
              )}
            </div>
          </section>
        )}

        {/* Navegação de Abas (Cantos Sutis e Tipografia Brand em Caixa Alta) */}
        <div className="grid grid-cols-2 sm:flex rounded-md bg-benedetto-card border border-benedetto-border p-1 gap-1">
          {temUnidadesVinculadas && (
            <button
              type="button"
              onClick={() => setAbaAtiva("unidade")}
              className={`flex-1 py-3 px-4 rounded-sm font-brand text-[11px] uppercase tracking-[0.2em] flex items-center justify-center gap-2 transition ${
                abaAtiva === "unidade"
                  ? "bg-benedetto-dark text-white"
                  : "text-benedetto-textMuted hover:text-benedetto-textMain"
              }`}
            >
              <Home className="w-3.5 h-3.5 text-benedetto-gold shrink-0" />
              <span>
                {obra && obra.unidades_vinculadas.length > 1
                  ? `Minhas Unidades (${obra.unidades_vinculadas.length})`
                  : "Minha Unidade"}
              </span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setAbaAtiva("diarios")}
            className={`flex-1 py-3 px-4 rounded-sm font-brand text-[11px] uppercase tracking-[0.2em] flex items-center justify-center gap-2 transition ${
              abaAtiva === "diarios"
                ? "bg-benedetto-dark text-white"
                : "text-benedetto-textMuted hover:text-benedetto-textMain"
            }`}
          >
            <ClipboardList className="w-3.5 h-3.5 text-benedetto-gold shrink-0" />
            <span>Diário Geral ({obra?.total_diarios ?? diarios.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setAbaAtiva("galeria")}
            className={`flex-1 py-3 px-4 rounded-sm font-brand text-[11px] uppercase tracking-[0.2em] flex items-center justify-center gap-2 transition ${
              abaAtiva === "galeria"
                ? "bg-benedetto-dark text-white"
                : "text-benedetto-textMuted hover:text-benedetto-textMain"
            }`}
          >
            <Images className="w-3.5 h-3.5 text-benedetto-gold shrink-0" />
            <span>Galeria ({todasFotosGeraisDaObra.length})</span>
          </button>

          {usuario?.perfil === "admin" && (
            <button
              type="button"
              onClick={() => setAbaAtiva("quarentena")}
              className={`flex-1 py-3 px-4 rounded-sm font-brand text-[11px] uppercase tracking-[0.2em] flex items-center justify-center gap-2 transition ${
                abaAtiva === "quarentena"
                  ? "bg-benedetto-gold text-benedetto-dark font-semibold"
                  : "text-amber-900 bg-amber-50/80 hover:bg-amber-100/80"
              }`}
            >
              <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
              <span>Curadoria ({fotosQuarentena.length})</span>
            </button>
          )}
        </div>

        {/* ABA 1 (PONTO X): Visão Exclusiva da Unidade do Condômino */}
        {abaAtiva === "unidade" && obra && temUnidadesVinculadas && (
          <section className="space-y-5">
            {/* Seletor caso o condômino possua mais de uma unidade (ex.: Apto 302 e Apto 501) */}
            {obra.unidades_vinculadas.length > 1 && (
              <div className="bg-benedetto-card rounded-md border border-benedetto-border p-4">
                <p className="font-brand text-[10px] uppercase tracking-[0.25em] text-benedetto-textMuted mb-3">
                  Selecione sua unidade autônoma
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {obra.unidades_vinculadas.map((u) => {
                    const selecionada = u.id === unidadeSelecionadaId;
                    return (
                      <button
                        key={u.id}
                        type="button"
                        onClick={() => void carregarUnidadeEspecifica(u.id)}
                        className={`p-4 rounded-md border text-left transition flex flex-col justify-between ${
                          selecionada
                            ? "bg-benedetto-dark text-white border-benedetto-dark"
                            : "bg-benedetto-bg hover:bg-white text-benedetto-textMain border-benedetto-border"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-brand text-xs uppercase tracking-[0.2em] font-medium truncate">
                            {u.identificador}
                          </span>
                          <span className="w-2 h-2 bg-benedetto-gold shrink-0" />
                        </div>
                        <div className="mt-3 flex items-center justify-between text-xs">
                          <span
                            className={
                              selecionada
                                ? "text-white/60"
                                : "text-benedetto-textMuted"
                            }
                          >
                            Avanço de Acabamentos
                          </span>
                          <span className="font-display text-lg text-benedetto-gold">
                            {Number(u.percentual_reforma)
                              .toFixed(0)
                              .replace(".", ",")}
                            %
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {carregandoUnidade ? (
              <div className="bg-benedetto-card rounded-md border border-benedetto-border p-12 text-center">
                <Loader2 className="w-6 h-6 text-benedetto-gold animate-spin mx-auto mb-3" />
                <p className="font-brand text-[11px] uppercase tracking-[0.2em] text-benedetto-textMuted">
                  Carregando dossiê da unidade...
                </p>
              </div>
            ) : (
              detalheUnidade && (
                <div className="bg-benedetto-card rounded-md border border-benedetto-border shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] overflow-hidden">
                  {/* Cabeçalho Escuro da Unidade */}
                  <div className="bg-benedetto-dark p-6 sm:p-7 text-white border-b border-benedetto-borderDark">
                    <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                      <div>
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-sm font-brand text-[10px] uppercase tracking-[0.2em] border mb-3 ${
                            traduzirStatusReforma(detalheUnidade.status_reforma)
                              .classes
                          }`}
                        >
                          {
                            traduzirStatusReforma(detalheUnidade.status_reforma)
                              .rotulo
                          }
                        </span>
                        <h2 className="font-brand font-light text-xl sm:text-3xl uppercase tracking-[0.25em] text-white">
                          {detalheUnidade.identificador}
                        </h2>
                        <p className="text-xs text-white/60 mt-1">
                          Dossiê privativo de acabamentos e personalização da
                          unidade
                        </p>
                      </div>

                      <div className="sm:text-right shrink-0">
                        <span className="font-brand text-[10px] uppercase tracking-[0.25em] text-white/60 block">
                          Evolução da Unidade
                        </span>
                        <span className="font-display text-3xl text-benedetto-gold">
                          {percentualUnidadeNumero.toFixed(1).replace(".", ",")}%
                        </span>
                      </div>
                    </div>

                    <div className="mt-5">
                      <div className="w-full h-1.5 bg-white/10 overflow-hidden">
                        <div
                          className="h-full bg-benedetto-gold transition-all duration-700"
                          style={{ width: `${percentualUnidadeNumero}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Corpo da Unidade */}
                  <div className="p-5 sm:p-6 space-y-6">
                    {detalheUnidade.observacoes_reforma && (
                      <div className="bg-benedetto-bg border-l-2 border-benedetto-gold rounded-md p-4 text-sm text-benedetto-textMain leading-relaxed">
                        <p className="font-brand text-[10px] uppercase tracking-[0.2em] text-benedetto-gold font-semibold mb-1.5">
                          Parecer Técnico da Engenharia
                        </p>
                        {detalheUnidade.observacoes_reforma}
                      </div>
                    )}

                    {/* Serviços Executados na Unidade */}
                    {detalheUnidade.tarefas.length > 0 && (
                      <div>
                        <h3 className="font-brand text-[11px] font-medium uppercase tracking-[0.2em] text-benedetto-textMuted flex items-center gap-2 mb-3">
                          <span className="w-1.5 h-1.5 bg-benedetto-gold inline-block" />
                          Acabamentos Executados na Unidade (
                          {detalheUnidade.tarefas.length})
                        </h3>
                        <ul className="divide-y divide-benedetto-border border border-benedetto-border rounded-md overflow-hidden">
                          {detalheUnidade.tarefas.map((tarefa) => {
                            const qtd =
                              tarefa.quantidade !== null &&
                              tarefa.quantidade !== undefined
                                ? Number(tarefa.quantidade)
                                : null;
                            return (
                              <li
                                key={tarefa.id}
                                className="p-3.5 sm:px-4 bg-white flex items-start justify-between gap-3"
                              >
                                <div className="flex items-start gap-3 min-w-0">
                                  <Check className="w-4 h-4 text-benedetto-gold shrink-0 mt-0.5" />
                                  <div>
                                    <p className="text-sm font-medium text-benedetto-textMain">
                                      {tarefa.descricao}
                                    </p>
                                    {tarefa.observacoes && (
                                      <p className="text-xs text-benedetto-textMuted mt-0.5">
                                        {tarefa.observacoes}
                                      </p>
                                    )}
                                  </div>
                                </div>
                                {qtd !== null && (
                                  <span className="text-xs font-medium bg-benedetto-bg text-benedetto-textMain px-2.5 py-1 rounded-sm border border-benedetto-border shrink-0">
                                    {qtd.toLocaleString("pt-BR")}{" "}
                                    {tarefa.unidade_medida || ""}
                                  </span>
                                )}
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}

                    {/* Fotos Exclusivas do Interior da Unidade (Proporção 4:5) */}
                    <div>
                      <h3 className="font-brand text-[11px] font-medium uppercase tracking-[0.2em] text-benedetto-textMuted flex items-center gap-2 mb-3">
                        <span className="w-1.5 h-1.5 bg-benedetto-gold inline-block" />
                        Registros Internos da Unidade (
                        {detalheUnidade.fotos.length})
                      </h3>

                      {detalheUnidade.fotos.length === 0 ? (
                        <div className="bg-benedetto-bg rounded-md border border-benedetto-border p-8 text-center text-xs text-benedetto-textMuted">
                          Nenhum registro fotográfico individual cadastrado até
                          o momento.
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                          {detalheUnidade.fotos.map((foto, index) => (
                            <button
                              key={foto.id}
                              type="button"
                              onClick={() => {
                                setLightboxFotos(detalheUnidade.fotos);
                                setLightboxIndice(index);
                              }}
                              className="group relative aspect-[4/5] rounded-md overflow-hidden bg-benedetto-dark border border-benedetto-border text-left focus:outline-none focus:ring-1 focus:ring-benedetto-gold"
                            >
                              <img
                                src={resolverUrlMidia(foto.url)}
                                alt={foto.descricao || "Foto da unidade"}
                                loading="lazy"
                                className="w-full h-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
                              />
                              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-benedetto-dark/90 via-benedetto-dark/40 to-transparent p-3 pt-8">
                                <p className="text-xs font-medium text-white line-clamp-1">
                                  {foto.descricao || "Ampliar imagem"}
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
                      )}
                    </div>
                  </div>
                </div>
              )
            )}
          </section>
        )}

        {/* ABA 2: Feed Cronológico de Diários GERAIS do Edifício */}
        {abaAtiva === "diarios" && (
          <section className="space-y-5">
            {diarios.length === 0 ? (
              <div className="bg-benedetto-card rounded-md border border-benedetto-border p-10 text-center">
                <ClipboardList className="w-8 h-8 text-benedetto-gold mx-auto mb-3" />
                <p className="font-display text-lg text-benedetto-textMain">
                  Nenhum diário de obra publicado até o momento.
                </p>
              </div>
            ) : (
              <>
                {diarios.map((diario, idx) => (
                  <DiarioCard
                    key={diario.id}
                    diario={diario}
                    expandidoInicialmente={idx === 0}
                    aoAbrirFoto={(fotos, indice) => {
                      setLightboxFotos(fotos);
                      setLightboxIndice(indice);
                    }}
                  />
                ))}

                {pagina < totalPaginas && (
                  <div className="pt-2 text-center">
                    <button
                      type="button"
                      onClick={handleCarregarMaisDiarios}
                      disabled={carregandoMais}
                      className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-md bg-benedetto-dark hover:bg-benedetto-cardDark text-white font-brand text-[11px] uppercase tracking-[0.2em] transition disabled:opacity-60"
                    >
                      {carregandoMais ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin text-benedetto-gold" />
                          Carregando...
                        </>
                      ) : (
                        "Carregar Relatórios Anteriores"
                      )}
                    </button>
                  </div>
                )}
              </>
            )}
          </section>
        )}

        {/* ABA 3: Galeria Consolidada de Fotos GERAIS do Edifício (Proporção 4:5) */}
        {abaAtiva === "galeria" && (
          <section className="bg-benedetto-card rounded-md border border-benedetto-border p-5 sm:p-6 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)]">
            {todasFotosGeraisDaObra.length === 0 ? (
              <div className="p-8 text-center">
                <Camera className="w-8 h-8 text-benedetto-gold mx-auto mb-2" />
                <p className="font-display text-base text-benedetto-textMain">
                  Nenhum registro fotográfico geral disponível.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3.5">
                {todasFotosGeraisDaObra.map((item, idx) => (
                  <button
                    key={item.foto.id}
                    type="button"
                    onClick={() => {
                      setLightboxFotos(
                        todasFotosGeraisDaObra.map((x) => x.foto)
                      );
                      setLightboxIndice(idx);
                    }}
                    className="group relative aspect-[4/5] rounded-md overflow-hidden bg-benedetto-dark border border-benedetto-border text-left focus:outline-none focus:ring-1 focus:ring-benedetto-gold"
                  >
                    <img
                      src={resolverUrlMidia(item.foto.url)}
                      alt={item.foto.descricao || "Foto da obra"}
                      loading="lazy"
                      className="w-full h-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
                    />
                    <span className="absolute top-2.5 left-2.5 font-brand text-[10px] uppercase tracking-[0.15em] px-2.5 py-1 rounded-sm bg-benedetto-dark/80 text-white border border-white/10">
                      {formatarDataBr(item.dataDiario)}
                    </span>
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-benedetto-dark/90 via-benedetto-dark/40 to-transparent p-3 pt-8">
                      <p className="text-xs font-medium text-white line-clamp-1">
                        {item.foto.descricao || "Registro da obra"}
                      </p>
                      {item.foto.local && (
                        <p className="font-brand text-[10px] uppercase tracking-[0.15em] text-benedetto-gold line-clamp-1 mt-1">
                          {item.foto.local}
                        </p>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>
        )}

        {/* ABA 4 (EXCLUSIVA ADMIN): Curadoria Rápida de Fotos em Quarentena */}
        {abaAtiva === "quarentena" && usuario?.perfil === "admin" && (
          <section className="space-y-4">
            <div className="bg-amber-50/70 border border-amber-200/70 rounded-md p-4 text-xs sm:text-sm text-amber-950">
              <p className="font-brand text-[11px] uppercase tracking-[0.2em] font-semibold flex items-center gap-2 mb-1.5">
                <ShieldAlert className="w-4 h-4 text-benedetto-gold shrink-0" />
                Curadoria de Privacidade (Ponto X — Fase de Reformas)
              </p>
              <p className="text-amber-900/90 leading-relaxed">
                Fotos recebidas do Sienge sem identificação explícita de unidade
                permanecem retidas em <strong>quarentena</strong> (ocultas dos
                condôminos). Selecione abaixo o destino correto com{" "}
                <strong>1 clique</strong>.
              </p>
            </div>

            {fotosQuarentena.length === 0 ? (
              <div className="bg-benedetto-card rounded-md border border-benedetto-border p-10 text-center">
                <Check className="w-8 h-8 text-benedetto-gold mx-auto mb-2" />
                <p className="font-display text-lg text-benedetto-textMain">
                  Nenhuma foto pendente de curadoria.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {fotosQuarentena.map((foto, idx) => (
                  <div
                    key={foto.id}
                    className="bg-benedetto-card rounded-md border border-benedetto-border p-4 flex flex-col sm:flex-row gap-5 items-start"
                  >
                    <button
                      type="button"
                      onClick={() => {
                        setLightboxFotos(
                          fotosQuarentena.map((f, i) => ({
                            id: f.id,
                            unidade_id: null,
                            url: f.url,
                            descricao: f.descricao,
                            local: f.local,
                            ordem: i,
                            largura: null,
                            altura: null,
                          }))
                        );
                        setLightboxIndice(idx);
                      }}
                      title="Clique para ampliar em tela cheia"
                      className="group relative w-full sm:w-44 aspect-[4/5] rounded-md overflow-hidden bg-benedetto-dark border border-benedetto-border shrink-0 text-left focus:outline-none focus:ring-1 focus:ring-benedetto-gold cursor-zoom-in"
                    >
                      <img
                        src={resolverUrlMidia(foto.url)}
                        alt={foto.descricao || "Foto em quarentena"}
                        className="w-full h-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
                      />
                      <span className="absolute bottom-2 right-2 px-2.5 py-1 rounded-sm bg-benedetto-dark/85 text-white group-hover:bg-benedetto-gold group-hover:text-benedetto-dark font-brand text-[9px] uppercase tracking-[0.18em] border border-white/15 transition">
                        Ampliar
                      </span>
                    </button>
                    <div className="flex-1 min-w-0 space-y-3 w-full">
                      <div>
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-sm font-brand text-[10px] uppercase tracking-[0.18em] bg-amber-50 text-amber-900 border border-amber-200/60">
                          Diário de {formatarDataBr(foto.data_diario)} • Retida
                        </span>
                        <h4 className="font-display text-lg text-benedetto-textMain mt-1.5">
                          {foto.descricao || "Sem descrição informada no Sienge"}
                        </h4>
                        <p className="text-xs text-benedetto-textMuted mt-0.5">
                          Local original no Sienge:{" "}
                          <strong className="text-benedetto-textMain">
                            {foto.local || "Não informado"}
                          </strong>
                        </p>
                      </div>

                      <div className="pt-3 border-t border-benedetto-border">
                        <p className="font-brand text-[10px] uppercase tracking-[0.2em] text-benedetto-textMuted mb-2.5">
                          Classificar e Publicar:
                        </p>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={classificandoFotoId === foto.id}
                            onClick={() =>
                              void handleClassificarFoto(foto.id, null)
                            }
                            className="px-3.5 py-2 rounded-md font-brand text-[10px] uppercase tracking-[0.18em] bg-benedetto-dark hover:bg-benedetto-cardDark text-white transition disabled:opacity-50"
                          >
                            Aprovar como Edifício Geral
                          </button>

                          {obra?.unidades_vinculadas.map((u) => (
                            <button
                              key={u.id}
                              type="button"
                              disabled={classificandoFotoId === foto.id}
                              onClick={() =>
                                void handleClassificarFoto(foto.id, u.id)
                              }
                              className="px-3.5 py-2 rounded-md font-brand text-[10px] uppercase tracking-[0.18em] bg-benedetto-gold hover:bg-benedetto-goldHover text-benedetto-dark font-semibold transition disabled:opacity-50"
                            >
                              Atribuir ao {u.identificador}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      {/* Lightbox Modal em Tela Cheia com Fundo Preto Profundo (#111215) */}
      {lightboxFotos && (
        <LightboxModal
          fotos={lightboxFotos}
          indiceAtual={lightboxIndice}
          aoFechar={() => setLightboxFotos(null)}
          aoMudarIndice={(novo) => setLightboxIndice(novo)}
        />
      )}

      {/* Modal de Gestão Administrativa da Obra (Percentual e Fase) */}
      {modalEditarObraAberto && obra && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md bg-benedetto-bg border border-benedetto-border rounded-lg shadow-2xl p-6 sm:p-8 overflow-hidden">
            <div className="flex items-center justify-between pb-4 mb-5 border-b border-benedetto-border">
              <div>
                <span className="font-brand text-[10px] uppercase tracking-[0.25em] text-benedetto-gold block">
                  Painel Administrativo
                </span>
                <h3 className="font-display text-xl text-benedetto-textMain mt-0.5">
                  Ajustar Evolução da Obra
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setModalEditarObraAberto(false)}
                className="p-1.5 rounded-full hover:bg-black/5 text-benedetto-textMuted hover:text-benedetto-textMain transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-benedetto-textMuted mb-6 font-medium">
              Defina a porcentagem real de avanço físico e a etapa do empreendimento{" "}
              <strong className="text-benedetto-textMain">{obra.nome}</strong>.
            </p>

            <form onSubmit={handleSalvarEdicaoObra} className="space-y-5">
              <div>
                <label className="block font-brand text-[11px] uppercase tracking-[0.2em] text-benedetto-textMuted mb-2">
                  Evolução Física Geral (%)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    required
                    value={editPercentual}
                    onChange={(e) => setEditPercentual(e.target.value)}
                    placeholder="Ex: 14.50"
                    className="w-full px-4 py-2.5 rounded-md bg-white border border-benedetto-border text-benedetto-textMain font-medium focus:outline-none focus:border-benedetto-gold focus:ring-1 focus:ring-benedetto-gold text-lg"
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-benedetto-textMuted font-bold text-sm pointer-events-none">
                    %
                  </span>
                </div>
              </div>

              <div>
                <label className="block font-brand text-[11px] uppercase tracking-[0.2em] text-benedetto-textMuted mb-2">
                  Fase Atual do Empreendimento
                </label>
                <select
                  value={editFase}
                  onChange={(e) => setEditFase(e.target.value as FaseObra)}
                  className="w-full px-4 py-2.5 rounded-md bg-white border border-benedetto-border text-benedetto-textMain font-medium focus:outline-none focus:border-benedetto-gold focus:ring-1 focus:ring-benedetto-gold text-sm"
                >
                  <option value="estrutural_geral">
                    1. Estrutural Geral (Fundação / Supraestrutura)
                  </option>
                  <option value="reformas_unidades">
                    2. Reformas das Unidades (Ponto X / Acabamentos)
                  </option>
                  <option value="entrega">
                    3. Entrega de Chaves (Vistoria Final)
                  </option>
                </select>
              </div>

              {erroEditarObra && (
                <div className="rounded-md bg-red-50 border border-red-200 px-3.5 py-2.5 text-xs text-red-800 font-medium">
                  {erroEditarObra}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  disabled={salvandoObra}
                  onClick={() => setModalEditarObraAberto(false)}
                  className="px-4 py-2.5 rounded-md font-brand text-[11px] uppercase tracking-[0.2em] text-benedetto-textMuted hover:text-benedetto-textMain transition disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={salvandoObra}
                  className="px-5 py-2.5 rounded-md font-brand text-[11px] uppercase tracking-[0.2em] bg-benedetto-dark hover:bg-benedetto-cardDark text-white font-medium transition flex items-center gap-2 disabled:opacity-60"
                >
                  {salvandoObra ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-benedetto-gold" />
                      <span>Salvando...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5 text-benedetto-gold" />
                      <span>Salvar Alterações</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal LGPD - Termo de Uso e Política de Privacidade no Primeiro Login */}
      {exibirModalPrivacidade && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-white border border-benedetto-border shadow-2xl p-6 sm:p-8 space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-benedetto-dark flex items-center justify-center text-benedetto-gold shadow-md shrink-0">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-serif text-xl font-bold text-benedetto-textMain">
                  Termos de Uso e Privacidade
                </h3>
                <p className="font-brand text-[10px] uppercase tracking-[0.2em] text-benedetto-gold font-semibold">
                  Conformidade com a LGPD (Lei nº 13.709/2018)
                </p>
              </div>
            </div>

            <div className="text-sm text-benedetto-textMuted space-y-3 leading-relaxed border-y border-benedetto-border/60 py-4 max-h-[300px] overflow-y-auto pr-1">
              <p>
                Bem-vindo ao <strong>Portal do Condômino Benedetto</strong>. Para garantir transparência e a segurança absoluta dos seus dados:
              </p>
              <div className="rounded-lg bg-benedetto-paper border border-benedetto-border p-3.5 space-y-2.5 text-xs text-benedetto-textMain">
                <div className="flex items-start gap-2">
                  <span className="font-bold text-benedetto-gold shrink-0">1. Base Legal:</span>
                  <span>O tratamento dos seus dados decorre da <strong>Execução de Contrato (Art. 7º, V da LGPD)</strong> para prestação de contas da evolução física da sua obra.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-benedetto-gold shrink-0">2. Confidencialidade:</span>
                  <span>Seu CPF, unidades e fotos das suas reformas são estritamente isolados e nunca são compartilhados com outros condôminos.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-benedetto-gold shrink-0">3. Segurança:</span>
                  <span>Seus registros trafegam por canais criptografados e as imagens são protegidas em nuvem segura.</span>
                </div>
              </div>
              <p className="text-xs">
                Ao prosseguir, você confirma a ciência sobre a utilização dos dados cadastrais necessários para o acesso ao portal.
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-1">
              <button
                type="button"
                disabled={aceitandoTermo}
                onClick={handleAceitarPrivacidade}
                className="w-full sm:w-auto px-6 py-3 rounded-md font-brand text-[11px] uppercase tracking-[0.2em] bg-benedetto-dark hover:bg-benedetto-cardDark text-white font-medium transition flex items-center justify-center gap-2 disabled:opacity-60 shadow-md"
              >
                {aceitandoTermo ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-benedetto-gold" />
                    <span>Registrando aceite...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4 text-benedetto-gold" />
                    <span>Li e Concordo com os Termos</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
