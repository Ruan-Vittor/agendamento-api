from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import List, Optional

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/agendamentos", tags=["Agendamentos"])


# ─────────────────────────────────────────────────────────────
# FUNÇÃO CENTRAL: valida se o horário solicitado está disponível
# ─────────────────────────────────────────────────────────────
def checar_conflito(
    db: Session,
    data_hora_inicio: datetime,
    duracao_min: int,
    ignorar_id: Optional[int] = None  # usado ao reagendar
) -> bool:
    """
    Retorna True se houver conflito de horário.

    Lógica: um novo agendamento [A_inicio, A_fim] conflita com
    um existente [B_inicio, B_fim] quando:
        A_inicio < B_fim  E  A_fim > B_inicio
    """
    data_hora_fim = data_hora_inicio + timedelta(minutes=duracao_min)

    query = db.query(models.Agendamento).join(models.Servico).filter(
        models.Agendamento.status != "cancelado"  # cancelados não bloqueiam horário
    )

    if ignorar_id:
        query = query.filter(models.Agendamento.id != ignorar_id)

    agendamentos_existentes = query.all()

    for ag in agendamentos_existentes:
        ag_inicio = ag.data_hora
        ag_fim = ag.data_hora + timedelta(minutes=ag.servico.duracao_min)

        # Checa sobreposição
        if data_hora_inicio < ag_fim and data_hora_fim > ag_inicio:
            return True, ag  # conflita, retorna o agendamento conflitante

    return False, None


# ── POST /agendamentos ────────────────────────────────────────
@router.post("/", response_model=schemas.AgendamentoResponse, status_code=status.HTTP_201_CREATED)
def criar_agendamento(dados: schemas.AgendamentoCreate, db: Session = Depends(get_db)):
    """
    Cria um novo agendamento.
    Valida automaticamente conflito de horário antes de confirmar.
    """
    # 1. Verifica se o cliente existe
    cliente = db.query(models.Cliente).filter(models.Cliente.id == dados.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # 2. Verifica se o serviço existe
    servico = db.query(models.Servico).filter(models.Servico.id == dados.servico_id).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    # 3. Não permite agendamento no passado
    # Remove fuso horário para comparação (normaliza para naive)
    data_hora_naive = dados.data_hora.replace(tzinfo=None)
    if data_hora_naive < datetime.now():
        raise HTTPException(status_code=400, detail="Não é possível agendar em uma data/hora passada")

    # 4. Verifica conflito de horário (usa datetime sem fuso)
    conflito, ag_conflitante = checar_conflito(db, data_hora_naive, servico.duracao_min)
    if conflito:
        ag_fim = ag_conflitante.data_hora + timedelta(minutes=ag_conflitante.servico.duracao_min)
        raise HTTPException(
            status_code=409,
            detail=(
                f"Conflito de horário! Já existe o agendamento #{ag_conflitante.id} "
                f"({ag_conflitante.cliente.nome}) das "
                f"{ag_conflitante.data_hora.strftime('%H:%M')} às {ag_fim.strftime('%H:%M')}."
            )
        )

    # 5. Cria o agendamento
    novo = models.Agendamento(
        cliente_id=dados.cliente_id,
        servico_id=dados.servico_id,
        data_hora=data_hora_naive,
        observacoes=dados.observacoes,
        status="agendado"
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


# ── GET /agendamentos ─────────────────────────────────────────
@router.get("/", response_model=List[schemas.AgendamentoResponse])
def listar_agendamentos(
    data: Optional[str] = None,       # filtra por data: "2024-12-25"
    cliente_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lista agendamentos com filtros opcionais por data, cliente e status."""
    query = db.query(models.Agendamento)

    if data:
        try:
            dia = datetime.strptime(data, "%Y-%m-%d")
            query = query.filter(
                and_(
                    models.Agendamento.data_hora >= dia,
                    models.Agendamento.data_hora < dia + timedelta(days=1)
                )
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido. Use: AAAA-MM-DD")

    if cliente_id:
        query = query.filter(models.Agendamento.cliente_id == cliente_id)

    if status:
        query = query.filter(models.Agendamento.status == status)

    return query.order_by(models.Agendamento.data_hora).all()


# ── GET /agendamentos/hoje ────────────────────────────────────
@router.get("/hoje", response_model=List[schemas.AgendamentoResponse])
def agendamentos_de_hoje(db: Session = Depends(get_db)):
    """Lista todos os agendamentos do dia atual, em ordem cronológica."""
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    amanha = hoje + timedelta(days=1)

    return (
        db.query(models.Agendamento)
        .filter(
            and_(
                models.Agendamento.data_hora >= hoje,
                models.Agendamento.data_hora < amanha,
                models.Agendamento.status != "cancelado"
            )
        )
        .order_by(models.Agendamento.data_hora)
        .all()
    )


# ── GET /agendamentos/{id} ────────────────────────────────────
@router.get("/{agendamento_id}", response_model=schemas.AgendamentoResponse)
def buscar_agendamento(agendamento_id: int, db: Session = Depends(get_db)):
    ag = db.query(models.Agendamento).filter(models.Agendamento.id == agendamento_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return ag


# ── PATCH /agendamentos/{id}/status ──────────────────────────
@router.patch("/{agendamento_id}/status", response_model=schemas.AgendamentoResponse)
def atualizar_status(
    agendamento_id: int,
    dados: schemas.AgendamentoStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza o status de um agendamento.

    Regras de transição:
    - agendado  → concluido | cancelado
    - concluido → não pode alterar
    - cancelado → não pode alterar

    Ao CONCLUIR: cria o registro de pagamento automaticamente como 'pendente'.
    """
    ag = db.query(models.Agendamento).filter(models.Agendamento.id == agendamento_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    # Bloqueia transições inválidas
    if ag.status == "concluido":
        raise HTTPException(status_code=400, detail="Agendamento já concluído. Não pode ser alterado.")
    if ag.status == "cancelado":
        raise HTTPException(status_code=400, detail="Agendamento cancelado. Não pode ser reaberto.")

    ag.status = dados.status

    # Ao concluir: cria o pagamento pendente automaticamente
    if dados.status == "concluido" and not ag.pagamento:
        pagamento = models.Pagamento(
            agendamento_id=ag.id,
            valor=ag.servico.preco,
            status="pendente"
        )
        db.add(pagamento)

    db.commit()
    db.refresh(ag)
    return ag


# ── PATCH /agendamentos/{id}/pagamento ───────────────────────
@router.patch("/{agendamento_id}/pagamento", response_model=schemas.PagamentoResponse)
def registrar_pagamento(
    agendamento_id: int,
    forma_pagamento: str,
    db: Session = Depends(get_db)
):
    """
    Marca o pagamento de um agendamento concluído como pago.
    Formas aceitas: dinheiro | pix | cartao
    """
    formas_validas = {"dinheiro", "pix", "cartao"}
    if forma_pagamento not in formas_validas:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pagamento inválida. Use: {formas_validas}"
        )

    ag = db.query(models.Agendamento).filter(models.Agendamento.id == agendamento_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    if ag.status != "concluido":
        raise HTTPException(
            status_code=400,
            detail="Só é possível registrar pagamento de agendamentos concluídos."
        )

    if not ag.pagamento:
        raise HTTPException(status_code=404, detail="Registro de pagamento não encontrado.")

    if ag.pagamento.status == "pago":
        raise HTTPException(status_code=400, detail="Este agendamento já foi pago.")

    ag.pagamento.status = "pago"
    ag.pagamento.forma_pagamento = forma_pagamento
    ag.pagamento.data_pagamento = datetime.now()

    db.commit()
    db.refresh(ag.pagamento)
    return ag.pagamento
