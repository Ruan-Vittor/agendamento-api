from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/clientes", tags=["Clientes"])


# ── POST /clientes ─────────────────────────────────────────
@router.post("/", response_model=schemas.ClienteResponse, status_code=status.HTTP_201_CREATED)
def criar_cliente(cliente: schemas.ClienteCreate, db: Session = Depends(get_db)):
    """Cadastra um novo cliente."""

    # Verifica se já existe cliente com o mesmo telefone
    existente = db.query(models.Cliente).filter(
        models.Cliente.telefone == cliente.telefone
    ).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Já existe um cliente com o telefone {cliente.telefone}"
        )

    novo_cliente = models.Cliente(**cliente.model_dump())
    db.add(novo_cliente)
    db.commit()
    db.refresh(novo_cliente)
    return novo_cliente


# ── GET /clientes ──────────────────────────────────────────
@router.get("/", response_model=List[schemas.ClienteResponse])
def listar_clientes(
    skip: int = 0,
    limit: int = 100,
    nome: str = None,
    db: Session = Depends(get_db)
):
    """Lista todos os clientes. Aceita filtro por nome e paginação."""
    query = db.query(models.Cliente)

    if nome:
        query = query.filter(models.Cliente.nome.ilike(f"%{nome}%"))

    return query.offset(skip).limit(limit).all()


# ── GET /clientes/{id} ─────────────────────────────────────
@router.get("/{cliente_id}", response_model=schemas.ClienteResponse)
def buscar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Busca um cliente pelo ID."""
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    return cliente


# ── PUT /clientes/{id} ─────────────────────────────────────
@router.put("/{cliente_id}", response_model=schemas.ClienteResponse)
def atualizar_cliente(
    cliente_id: int,
    dados: schemas.ClienteUpdate,
    db: Session = Depends(get_db)
):
    """Atualiza os dados de um cliente."""
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Atualiza apenas os campos enviados (ignora None)
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(cliente, campo, valor)

    db.commit()
    db.refresh(cliente)
    return cliente


# ── DELETE /clientes/{id} ──────────────────────────────────
@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Remove um cliente. Só é possível se ele não tiver agendamentos."""
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Impede deletar cliente com agendamentos vinculados
    if cliente.agendamentos:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir um cliente com agendamentos. Cancele os agendamentos primeiro."
        )

    db.delete(cliente)
    db.commit()
