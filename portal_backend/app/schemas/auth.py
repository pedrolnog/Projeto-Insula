"""Schemas Pydantic v2 para autenticação por CPF e sessão do usuário."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import normalizar_cpf
from app.models.enums import PerfilUsuario


class LoginRequest(BaseModel):
    cpf: str = Field(..., description="CPF do condômino (com ou sem máscara)", examples=["111.222.333-44"])
    senha: str = Field(..., min_length=1, description="Senha de acesso ao portal")

    @field_validator("cpf")
    @classmethod
    def validar_e_limpar_cpf(cls, valor: str) -> str:
        cpf_limpo = normalizar_cpf(valor)
        if len(cpf_limpo) != 11:
            raise ValueError("O CPF deve conter exatamente 11 dígitos numéricos.")
        return cpf_limpo


class UsuarioResumoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cpf: str
    nome: str
    email: str | None = None
    telefone: str | None = None
    perfil: PerfilUsuario
    termo_privacidade_aceito_em: datetime | None = None


class AceiteTermoPrivacidadeResponse(BaseModel):
    mensagem: str
    termo_privacidade_aceito_em: datetime


class CriarUsuarioRequest(BaseModel):
    cpf: str = Field(..., description="CPF do usuário (com ou sem pontuação)", examples=["123.456.789-00"])
    nome: str = Field(..., min_length=2, max_length=150, description="Nome completo")
    senha: str = Field(..., min_length=6, max_length=128, description="Senha de acesso (mínimo 6 caracteres)")
    email: str | None = Field(None, max_length=120)
    telefone: str | None = Field(None, max_length=30)
    perfil: PerfilUsuario = Field(PerfilUsuario.CONDOMINO, description="Perfil do usuário: admin ou condomino")
    obras_ids: list[int] = Field(default_factory=list, description="Lista de IDs das obras vinculadas")
    unidades_ids: list[int] = Field(default_factory=list, description="Lista de IDs das unidades autônomas vinculadas")

    @field_validator("cpf")
    @classmethod
    def validar_e_limpar_cpf(cls, valor: str) -> str:
        cpf_limpo = normalizar_cpf(valor)
        if len(cpf_limpo) != 11:
            raise ValueError("O CPF deve conter exatamente 11 dígitos numéricos.")
        return cpf_limpo

    @field_validator("obras_ids", "unidades_ids")
    @classmethod
    def deduplicar_ids(cls, valor: list[int]) -> list[int]:
        return list(dict.fromkeys(valor))


class AtualizarUsuarioRequest(BaseModel):
    cpf: str | None = Field(None, description="Novo CPF do usuário (com ou sem pontuação)")
    nome: str | None = Field(None, min_length=2, max_length=150, description="Novo nome completo")
    senha: str | None = Field(None, min_length=6, max_length=128, description="Nova senha (opcional)")
    email: str | None = Field(None, max_length=120)
    telefone: str | None = Field(None, max_length=30)
    perfil: PerfilUsuario | None = Field(None, description="Novo perfil: admin ou condomino")
    ativo: bool | None = Field(None, description="Ativa ou desativa o acesso do usuário")
    obras_ids: list[int] | None = Field(
        None,
        description="Se informado, substitui a lista de IDs das obras vinculadas ao usuário",
    )
    unidades_ids: list[int] | None = Field(
        None,
        description="Se informado, substitui a lista de IDs das unidades vinculadas ao usuário",
    )

    @field_validator("cpf")
    @classmethod
    def validar_e_limpar_cpf_opcional(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        cpf_limpo = normalizar_cpf(valor)
        if len(cpf_limpo) != 11:
            raise ValueError("O CPF deve conter exatamente 11 dígitos numéricos.")
        return cpf_limpo

    @field_validator("obras_ids", "unidades_ids")
    @classmethod
    def deduplicar_ids_opcionais(cls, valor: list[int] | None) -> list[int] | None:
        if valor is None:
            return None
        return list(dict.fromkeys(valor))


class UsuarioAdminSchema(UsuarioResumoSchema):
    ativo: bool
    obras_vinculadas_ids: list[int] = Field(default_factory=list)
    unidades_vinculadas_ids: list[int] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UsuarioResumoSchema
