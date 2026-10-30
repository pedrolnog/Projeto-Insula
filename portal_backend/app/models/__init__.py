# Todo model novo precisa ser importado aqui para entrar no Base.metadata
# (é assim que o Alembic o enxerga no --autogenerate).
from app.models.base import Base
from app.models.diario import DiarioObra
from app.models.empresa import Empresa
from app.models.foto import FotoDiario
from app.models.log_sincronizacao import LogSincronizacao
from app.models.obra import Obra
from app.models.tarefa import TarefaDiario
from app.models.unidade import Unidade, usuarios_unidades
from app.models.usuario import Usuario, usuarios_obras

__all__ = [
    "Base",
    "DiarioObra",
    "Empresa",
    "FotoDiario",
    "LogSincronizacao",
    "Obra",
    "TarefaDiario",
    "Unidade",
    "Usuario",
    "usuarios_obras",
    "usuarios_unidades",
]
