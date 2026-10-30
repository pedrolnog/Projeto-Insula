/**
 * Contratos tipados e cliente HTTP para comunicação com o BFF FastAPI (`/api/v1`).
 * Regra arquitetural: o frontend NUNCA conversa com o Sienge diretamente.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

export interface UsuarioResumo {
  id: number;
  cpf: string;
  nome: string;
  email: string | null;
  telefone: string | null;
  perfil: "condomino" | "admin";
  termo_privacidade_aceito_em?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  usuario: UsuarioResumo;
}

export type FaseObra = "estrutural_geral" | "reformas_unidades" | "entrega";
export type StatusReformaUnidade = "nao_iniciada" | "em_andamento" | "concluida";

export interface ObraVinculadaResumo {
  id: number;
  nome: string;
  cidade: string | null;
  uf: string | null;
  fase_atual?: FaseObra;
  percentual_concluido: number | string | null;
  imagem_capa_url: string | null;
}

export interface UnidadeVinculadaResumo {
  id: number;
  obra_id: number;
  identificador: string;
  status_reforma: StatusReformaUnidade;
  percentual_reforma: number | string;
  observacoes_reforma: string | null;
  total_fotos: number;
}

export interface MinhaUnidadeDetalheResponse {
  id: number;
  obra_id: number;
  obra_nome: string;
  identificador: string;
  status_reforma: StatusReformaUnidade;
  percentual_reforma: number | string;
  observacoes_reforma: string | null;
  atualizado_em: string | null;
  fotos: FotoDiario[];
  tarefas: TarefaDiario[];
}

export interface MinhaObraResponse {
  id: number;
  nome: string;
  descricao: string | null;
  endereco: string | null;
  cidade: string | null;
  uf: string | null;
  situacao: string | null;
  fase_atual: FaseObra;
  percentual_concluido: number | string | null;
  data_inicio: string | null;
  data_previsao_entrega: string | null;
  imagem_capa_url: string | null;
  sincronizado_em: string | null;
  total_diarios: number;
  total_fotos: number;
  ultimo_diario_data: string | null;
  obras_vinculadas: ObraVinculadaResumo[];
  unidades_vinculadas: UnidadeVinculadaResumo[];
}

export interface FotoDiario {
  id: number;
  unidade_id?: number | null;
  url: string;
  descricao: string | null;
  local: string | null;
  ordem: number;
  largura: number | null;
  altura: number | null;
}

export interface TarefaDiario {
  id: number;
  unidade_id?: number | null;
  tipo: "planejada" | "avulsa";
  descricao: string | null;
  quantidade: number | string | null;
  unidade_medida: string | null;
  observacoes: string | null;
}

export interface TurnoDiario {
  descricao?: string;
  inicio?: string;
  fim?: string;
  clima?: string;
}

export interface OcorrenciaDiario {
  descricao?: string;
  tipo?: string;
}

export interface DiarioObra {
  id: number;
  obra_id: number;
  data: string;
  dia_semana: string | null;
  responsavel: string | null;
  observacoes: string | null;
  indice_pluviometrico: number | string | null;
  turnos: TurnoDiario[];
  ocorrencias: OcorrenciaDiario[];
  tarefas: TarefaDiario[];
  fotos: FotoDiario[];
}

export interface FotoQuarentenaAdmin {
  id: number;
  diario_id: number;
  obra_id: number;
  obra_nome: string;
  data_diario: string;
  url: string;
  descricao: string | null;
  local: string | null;
  unidade_id: number | null;
  publicado: boolean;
}

export interface DiariosPaginadosResponse {
  obra_id: number;
  obra_nome: string;
  total: number;
  pagina: number;
  tamanho_pagina: number;
  total_paginas: number;
  itens: DiarioObra[];
}

const TOKEN_STORAGE_KEY = "benedetto_portal_token";
const USER_STORAGE_KEY = "benedetto_portal_user";

export function salvarSessao(token: string, usuario: UsuarioResumo): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(usuario));
}

export function obterTokenSalvo(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function obterUsuarioSalvo(): UsuarioResumo | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UsuarioResumo;
  } catch {
    return null;
  }
}

export function limparSessao(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(USER_STORAGE_KEY);
}

export function resolverUrlMidia(url: string | null | undefined): string {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  const caminho = url.startsWith("/") ? url : `/${url}`;
  return `${API_BASE_URL}${caminho}`;
}

export function formatarCpfMascara(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 11);
  if (digitos.length <= 3) return digitos;
  if (digitos.length <= 6) return `${digitos.slice(0, 3)}.${digitos.slice(3)}`;
  if (digitos.length <= 9) {
    return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6)}`;
  }
  return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6, 9)}-${digitos.slice(9, 11)}`;
}

export function formatarDataBr(isoDate: string | null | undefined): string {
  if (!isoDate) return "—";
  const partes = isoDate.split("T")[0].split("-");
  if (partes.length === 3) {
    return `${partes[2]}/${partes[1]}/${partes[0]}`;
  }
  return isoDate;
}

export function formatarDataHoraBr(isoDateTime: string | null | undefined): string {
  if (!isoDateTime) return "—";
  const d = new Date(isoDateTime);
  if (Number.isNaN(d.getTime())) return isoDateTime;
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function requisitarApi<T>(path: string, init?: RequestInit): Promise<T> {
  const token = obterTokenSalvo();
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const resposta = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (resposta.status === 401 && !path.includes("/auth/login")) {
    limparSessao();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Sessão expirada. Faça login novamente.");
  }

  if (!resposta.ok) {
    let detalhe = `Erro HTTP ${resposta.status}`;
    try {
      const payloadErro = await resposta.json();
      if (typeof payloadErro?.detail === "string") {
        detalhe = payloadErro.detail;
      } else if (Array.isArray(payloadErro?.detail)) {
        detalhe = payloadErro.detail.map((e: { msg?: string }) => e.msg).join(", ");
      }
    } catch {
      // ignora erro de parse
    }
    throw new Error(detalhe);
  }

  return (await resposta.json()) as T;
}

export async function autenticarPorCpf(cpf: string, senha: string): Promise<TokenResponse> {
  const dados = await requisitarApi<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ cpf, senha }),
  });
  salvarSessao(dados.access_token, dados.usuario);
  return dados;
}

export async function buscarMinhaObra(obraId?: number | null): Promise<MinhaObraResponse> {
  const query = obraId ? `?obra_id=${obraId}` : "";
  return requisitarApi<MinhaObraResponse>(`/api/v1/minha-obra${query}`);
}

export async function buscarDetalheMinhaUnidade(
  unidadeId: number
): Promise<MinhaUnidadeDetalheResponse> {
  return requisitarApi<MinhaUnidadeDetalheResponse>(`/api/v1/minha-obra/unidades/${unidadeId}`);
}

export async function listarDiariosMinhaObra(params: {
  obraId?: number | null;
  pagina?: number;
  tamanhoPagina?: number;
}): Promise<DiariosPaginadosResponse> {
  const search = new URLSearchParams();
  if (params.obraId) search.set("obra_id", String(params.obraId));
  search.set("pagina", String(params.pagina ?? 1));
  search.set("tamanho_pagina", String(params.tamanhoPagina ?? 10));
  return requisitarApi<DiariosPaginadosResponse>(`/api/v1/minha-obra/diarios?${search.toString()}`);
}

export async function dispararSincronizacaoAdmin(obraId?: number | null): Promise<void> {
  const query = obraId ? `?obra_id=${obraId}` : "";
  await requisitarApi(`/api/v1/sync${query}`, { method: "POST" });
}

export async function listarFotosQuarentenaAdmin(
  obraId?: number | null
): Promise<FotoQuarentenaAdmin[]> {
  const query = obraId ? `?obra_id=${obraId}&apenas_pendentes=true` : "?apenas_pendentes=true";
  return requisitarApi<FotoQuarentenaAdmin[]>(`/api/v1/admin/fotos-quarentena${query}`);
}

export async function classificarFotoQuarentenaAdmin(
  fotoId: number,
  payload: { unidade_id: number | null; publicado: boolean; descricao?: string | null; local?: string | null }
): Promise<FotoQuarentenaAdmin> {
  return requisitarApi<FotoQuarentenaAdmin>(`/api/v1/admin/fotos/${fotoId}/classificar`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function atualizarObraAdmin(
  obraId: number,
  payload: {
    fase_atual?: FaseObra;
    percentual_concluido?: number | string | null;
    situacao?: string | null;
  }
): Promise<{
  obra_id: number;
  nome: string;
  fase_atual: FaseObra;
  percentual_concluido: number | null;
  situacao?: string | null;
}> {
  return requisitarApi(`/api/v1/admin/obras/${obraId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function aceitarTermoPrivacidade(): Promise<{
  mensagem: string;
  termo_privacidade_aceito_em: string;
}> {
  return requisitarApi("/api/v1/auth/aceitar-termo-privacidade", {
    method: "POST",
  });
}
