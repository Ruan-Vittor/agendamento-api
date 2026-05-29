from fastapi import FastAPI
from app.database import engine
from app import models
from app.routers import clientes, servicos, agendamentos, relatorios

# Cria todas as tabelas no banco ao iniciar (se ainda não existirem)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Agendamento",
    description="API para gerenciar agendamentos de profissionais autônomos",
    version="1.0.0"
)

# Routers
app.include_router(clientes.router)
app.include_router(servicos.router)
app.include_router(agendamentos.router)
app.include_router(relatorios.router)


@app.get("/")
def root():
    return {"mensagem": "Sistema de Agendamento rodando!", "versao": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
