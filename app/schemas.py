from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional


# ─────────────────────────────────────────
# CLIENTE
# ─────────────────────────────────────────

class ClienteBase(BaseModel):
    nome: str
    telefone: str
    email: Optional[str] = None

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v):
        if not v.strip():
            raise ValueError("Nome não pode ser vazio")
        return v.strip()

    @field_validator("telefone")
    @classmethod
    def telefone_valido(cls, v):
        apenas_numeros = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not apenas_numeros.isdigit() or len(apenas_numeros) < 10:
            raise ValueError("Telefone inválido. Use formato: (61) 99999-0000")
        return v


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None


class ClienteResponse(ClienteBase):
    id: int
    data_cadastro: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# SERVIÇO
# ─────────────────────────────────────────

class ServicoBase(BaseModel):
    nome: str
    duracao_min: int
    preco: float
    descricao: Optional[str] = None

    @field_validator("duracao_min")
    @classmethod
    def duracao_positiva(cls, v):
        if v <= 0:
            raise ValueError("Duração deve ser maior que zero")
        return v

    @field_validator("preco")
    @classmethod
    def preco_positivo(cls, v):
        if v < 0:
            raise ValueError("Preço não pode ser negativo")
        return v


class ServicoCreate(ServicoBase):
    pass


class ServicoUpdate(BaseModel):
    nome: Optional[str] = None
    duracao_min: Optional[int] = None
    preco: Optional[float] = None
    descricao: Optional[str] = None


class ServicoResponse(ServicoBase):
    id: int

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# AGENDAMENTO (usado nas fases seguintes)
# ─────────────────────────────────────────

class AgendamentoCreate(BaseModel):
    cliente_id: int
    servico_id: int
    data_hora: datetime
    observacoes: Optional[str] = None


class AgendamentoStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valido(cls, v):
        permitidos = {"agendado", "concluido", "cancelado"}
        if v not in permitidos:
            raise ValueError(f"Status inválido. Use: {permitidos}")
        return v


class AgendamentoResponse(BaseModel):
    id: int
    cliente_id: int
    servico_id: int
    data_hora: datetime
    status: str
    observacoes: Optional[str]
    cliente: ClienteResponse
    servico: ServicoResponse

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# PAGAMENTO (usado nas fases seguintes)
# ─────────────────────────────────────────

class PagamentoResponse(BaseModel):
    id: int
    agendamento_id: int
    valor: float
    forma_pagamento: Optional[str]
    status: str
    data_pagamento: Optional[datetime]

    model_config = {"from_attributes": True}
