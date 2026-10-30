"""Schemas Pydantic v2 para os endpoints do Condômino (Obra, Unidades, Diários, Tarefas e Fotos)."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import FaseObra, StatusReformaUnidade, TipoTarefa


class ObraVinculadaResumoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    cidade: str | None = None
    uf: str | None = None
    fase_atual: FaseObra = FaseObra.ESTRUTURAL_GERAL
    percentual_concluido: Decimal | None = None
    imagem_capa_url: str | None = None


class FotoDiarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unidade_id: int | None = None
    url: str
    descricao: str | None = None
    local: str | None = None
    ordem: int = 0
    largura: int | None = None
    altura: int | None = None


class TarefaDiarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unidade_id: int | None = None
    tipo: TipoTarefa
    descricao: str | None = None
    quantidade: Decimal | None = None
    unidade_medida: str | None = None
    observacoes: str | None = None


class UnidadeVinculadaResumoSchema(BaseModel):
    """Resumo de cada unidade pertencente exclusivamente ao condômino logado na obra."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    obra_id: int
    identificador: str
    status_reforma: StatusReformaUnidade
    percentual_reforma: Decimal
    observacoes_reforma: str | None = None
    total_fotos: int = 0


class MinhaUnidadeDetalheResponse(BaseModel):
    """Detalhes completos de uma unidade específica do condômino (Ponto X: Reformas)."""

    id: int
    obra_id: int
    obra_nome: str
    identificador: str
    status_reforma: StatusReformaUnidade
    percentual_reforma: Decimal
    observacoes_reforma: str | None = None
    atualizado_em: datetime | None = None
    total_fotos: int = 0
    pagina_fotos: int = 1
    tamanho_pagina_fotos: int = 20
    total_paginas_fotos: int = 1
    fotos: list[FotoDiarioSchema] = []
    tarefas: list[TarefaDiarioSchema] = []


class MinhaObraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    descricao: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    uf: str | None = None
    situacao: str | None = None
    fase_atual: FaseObra = FaseObra.ESTRUTURAL_GERAL
    percentual_concluido: Decimal | None = None
    data_inicio: date | None = None
    data_previsao_entrega: date | None = None
    imagem_capa_url: str | None = None
    sincronizado_em: datetime | None = None

    # Indicadores agregados (apenas itens gerais do edifício: unidade_id IS NULL)
    total_diarios: int = 0
    total_fotos: int = 0
    ultimo_diario_data: date | None = None

    # Permite ao condômino alternar caso invista em mais de uma obra
    obras_vinculadas: list[ObraVinculadaResumoSchema] = []

    # Unidades que pertencem EXCLUSIVAMENTE ao condômino logado nesta obra
    unidades_vinculadas: list[UnidadeVinculadaResumoSchema] = []


class DiarioObraSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    obra_id: int
    data: date
    dia_semana: str | None = None
    responsavel: str | None = None
    observacoes: str | None = None
    indice_pluviometrico: Decimal | None = None
    turnos: list[dict[str, Any]] = []
    ocorrencias: list[dict[str, Any]] = []
    tarefas: list[TarefaDiarioSchema] = []
    fotos: list[FotoDiarioSchema] = []


class FotoQuarentenaAdminSchema(BaseModel):
    """Foto retida em quarentena aguardando curadoria/classificação do engenheiro/admin."""

    id: int
    diario_id: int
    obra_id: int
    obra_nome: str
    data_diario: date
    url: str
    descricao: str | None = None
    local: str | None = None
    unidade_id: int | None = None
    publicado: bool = False


class ClassificarFotoRequest(BaseModel):
    """Decisão de curadoria do Admin para uma foto em quarentena."""

    unidade_id: int | None = None  # None = Área Comum / Geral do Edifício; ID = Unidade específica
    publicado: bool = True
    descricao: str | None = None
    local: str | None = None


class AlterarFaseObraRequest(BaseModel):
    """Permite ao Admin virar a chave da obra para o Ponto X (`reformas_unidades`) ou `entrega`."""

    fase_atual: FaseObra


class AtualizarObraAdminRequest(BaseModel):
    """Permite ao Admin atualizar percentual de evolução física geral, fase e previsão de entrega."""

    fase_atual: FaseObra | None = None
    percentual_concluido: Decimal | None = None
    situacao: str | None = None
    data_previsao_entrega: date | None = None


class DiariosPaginadosResponse(BaseModel):
    obra_id: int
    obra_nome: str
    total: int
    pagina: int
    tamanho_pagina: int
    total_paginas: int
    itens: list[DiarioObraSchema]
