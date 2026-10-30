"""Contrato do cliente Sienge.

O resto do sistema depende só desta interface, nunca da implementação.
Assim dá para trocar HTTP real <-> mock (ou outra fonte) sem mexer na ingestão.
Os métodos devolvem o JSON do Sienge como veio (dicts); a tradução para o
nosso modelo fica em app/services/sienge_mapper.py.
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Self

Json = dict[str, Any]


class SiengeClient(ABC):
    def __init__(self) -> None:
        # Contador de chamadas HTTP feitas (vai para logs_sincronizacao).
        self.requisicoes = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.fechar()

    async def fechar(self) -> None:
        pass

    # --- Empreendimentos -------------------------------------------------
    @abstractmethod
    async def listar_empreendimentos(self) -> list[Json]:
        """GET /enterprises (todas as páginas)."""

    # --- Diário de obra --------------------------------------------------
    @abstractmethod
    async def listar_diarios(self, building_id: int, inicio: date, fim: date) -> list[Json]:
        """GET /construction-daily-report (resumo, todas as páginas)."""

    @abstractmethod
    async def obter_diario(self, building_id: int, diario_id: int) -> Json:
        """GET /construction-daily-report/{buildingId}/{id} (completo)."""

    @abstractmethod
    async def baixar_anexo(self, building_id: int, diario_id: int, attachment_number: int) -> bytes:
        """GET .../attachments/{attachmentNumber} (binário)."""

    # --- Planejamento ----------------------------------------------------
    @abstractmethod
    async def listar_tarefas_planejamento(self, building_id: int, building_unit_id: int) -> list[Json]:
        """GET /building-projects/{buildingId}/sheets/{buildingUnitId}/tasks."""

    @abstractmethod
    async def listar_medicoes(self, building_id: int) -> list[Json]:
        """GET /building-projects/progress-logs?buildingId=..."""

    @abstractmethod
    async def obter_medicao(self, building_id: int, measurement_number: int) -> Json:
        """GET /building-projects/{buildingId}/progress-logs/{measurementNumber}."""

    @abstractmethod
    async def listar_itens_medicao(
        self, building_id: int, measurement_number: int, building_unit_id: int
    ) -> list[Json]:
        """GET .../progress-logs/{measurementNumber}/items/{buildingUnitId}."""
