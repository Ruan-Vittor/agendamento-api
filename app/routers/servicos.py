from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/servicos", tags=["Serviços"])


# ── POST /servicos ─────────────────────────────────────────
@router.post("/", response_model=schemas.ServicoResponse, status_code=status.HTTP_201_CREATED)
def criar_servico(servico: schemas.ServicoCreate, db: Session = Depends(get_db)):
    """Cadastra um novo serviço."""

    # Verifica nome duplicado
    existente = db.query(models.Servico).filter(
        models.Servico.nome.ilike(servico.nome)
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Já existe um serviço com o nome '{servico.nome}'")

    novo_servico = models.Servico(**servico.model_dump())
    db.add(novo_servico)
    db.commit()
    db.refresh(novo_servico)
    return novo_servico


# ── GET /servicos ──────────────────────────────────────────
@router.get("/", response_model=List[schemas.ServicoResponse])
def listar_servicos(db: Session = Depends(get_db)):
    """Lista todos os serviços disponíveis."""
    return db.query(models.Servico).all()


# ── GET /servicos/{id} ─────────────────────────────────────
@router.get("/{servico_id}", response_model=schemas.ServicoResponse)
def buscar_servico(servico_id: int, db: Session = Depends(get_db)):
    """Busca um serviço pelo ID."""
    servico = db.query(models.Servico).filter(models.Servico.id == servico_id).first()

    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    return servico


# ── PUT /servicos/{id} ─────────────────────────────────────
@router.put("/{servico_id}", response_model=schemas.ServicoResponse)
def atualizar_servico(
    servico_id: int,
    dados: schemas.ServicoUpdate,
    db: Session = Depends(get_db)
):
    """Atualiza os dados de um serviço."""
    servico = db.query(models.Servico).filter(models.Servico.id == servico_id).first()

    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(servico, campo, valor)

    db.commit()
    db.refresh(servico)
    return servico


# ── DELETE /servicos/{id} ──────────────────────────────────
@router.delete("/{servico_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_servico(servico_id: int, db: Session = Depends(get_db)):
    """Remove um serviço. Só é possível se ele não tiver agendamentos."""
    servico = db.query(models.Servico).filter(models.Servico.id == servico_id).first()

    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    if servico.agendamentos:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir um serviço com agendamentos vinculados."
        )

    db.delete(servico)
    db.commit()
