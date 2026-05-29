from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    telefone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    data_cadastro = Column(DateTime, default=func.now())

    # Relacionamento: um cliente pode ter vários agendamentos
    agendamentos = relationship("Agendamento", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente(id={self.id}, nome={self.nome})>"


class Servico(Base):
    __tablename__ = "servicos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    duracao_min = Column(Integer, nullable=False)  # duração em minutos
    preco = Column(Float, nullable=False)
    descricao = Column(Text, nullable=True)

    # Relacionamento: um serviço pode estar em vários agendamentos
    agendamentos = relationship("Agendamento", back_populates="servico")

    def __repr__(self):
        return f"<Servico(id={self.id}, nome={self.nome}, duracao={self.duracao_min}min)>"


class Agendamento(Base):
    __tablename__ = "agendamentos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    servico_id = Column(Integer, ForeignKey("servicos.id"), nullable=False)
    data_hora = Column(DateTime, nullable=False)  # início do atendimento
    status = Column(String(20), default="agendado")  # agendado | concluido | cancelado
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="agendamentos")
    servico = relationship("Servico", back_populates="agendamentos")
    pagamento = relationship("Pagamento", back_populates="agendamento", uselist=False)

    def __repr__(self):
        return f"<Agendamento(id={self.id}, cliente_id={self.cliente_id}, data={self.data_hora})>"


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    agendamento_id = Column(Integer, ForeignKey("agendamentos.id"), nullable=False)
    valor = Column(Float, nullable=False)
    forma_pagamento = Column(String(30), nullable=True)  # dinheiro | pix | cartao
    status = Column(String(20), default="pendente")  # pendente | pago
    data_pagamento = Column(DateTime, nullable=True)

    # Relacionamento
    agendamento = relationship("Agendamento", back_populates="pagamento")

    def __repr__(self):
        return f"<Pagamento(id={self.id}, valor={self.valor}, status={self.status})>"
