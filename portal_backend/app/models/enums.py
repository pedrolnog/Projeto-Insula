"""Enums de domínio.

São gravados como VARCHAR (native_enum=False) em vez de ENUM nativo do
PostgreSQL. Assim, adicionar um novo valor é só editar a classe aqui,
sem migração de ALTER TYPE.
"""
import enum

from sqlalchemy import Enum


def enum_column(enum_cls: type[enum.Enum], length: int = 20) -> Enum:
    return Enum(
        enum_cls,
        native_enum=False,
        create_constraint=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
    )


class PerfilUsuario(str, enum.Enum):
    CONDOMINO = "condomino"
    ADMIN = "admin"


class TipoTarefa(str, enum.Enum):
    PLANEJADA = "planejada"  # plannedTasks do Sienge (vinculada ao planejamento)
    AVULSA = "avulsa"  # detachedTasks do Sienge


class StatusFoto(str, enum.Enum):
    PENDENTE = "pendente"  # metadados salvos, arquivo ainda não processado
    PROCESSADA = "processada"  # convertida para WebP e enviada ao storage
    ERRO = "erro"


class OrigemSincronizacao(str, enum.Enum):
    CRON = "cron"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class StatusSincronizacao(str, enum.Enum):
    EXECUTANDO = "executando"
    SUCESSO = "sucesso"
    PARCIAL = "parcial"  # terminou, mas com falhas pontuais (ex.: algumas fotos)
    ERRO = "erro"


class FaseObra(str, enum.Enum):
    ESTRUTURAL_GERAL = "estrutural_geral"
    REFORMAS_UNIDADES = "reformas_unidades"
    ENTREGA = "entrega"


class StatusReformaUnidade(str, enum.Enum):
    NAO_INICIADA = "nao_iniciada"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
