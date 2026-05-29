# 📅 Sistema de Agendamento para Autônomos

API REST para gerenciamento de agendamentos, clientes, serviços e pagamentos — desenvolvida com **FastAPI**, **SQLAlchemy** e **SQLite**.

## 🚀 Tecnologias
- **Python 3.11+**
- **FastAPI** — framework web moderno e de alta performance
- **SQLAlchemy** — ORM para banco de dados
- **SQLite** — banco de dados local, sem necessidade de instalação
- **Pydantic** — validação de dados
- **ReportLab** — geração de relatórios em PDF

## 📦 Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/agendamento-app.git
cd agendamento-app

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Rode o servidor
uvicorn app.main:app --reload
```

## 📡 Endpoints disponíveis

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Status da API |
| POST | `/clientes` | Cadastrar cliente |
| GET | `/clientes` | Listar clientes |
| GET | `/clientes/{id}` | Buscar cliente |
| PUT | `/clientes/{id}` | Editar cliente |
| POST | `/servicos` | Cadastrar serviço |
| GET | `/servicos` | Listar serviços |
| POST | `/agendamentos` | Criar agendamento |
| GET | `/agendamentos` | Listar agendamentos |
| PATCH | `/agendamentos/{id}/status` | Atualizar status |
| GET | `/relatorio` | Relatório mensal em PDF |

## 📂 Estrutura do projeto

```
agendamento-app/
├── app/
│   ├── main.py           # Aplicação FastAPI
│   ├── database.py       # Conexão com o banco
│   ├── models.py         # Modelos das tabelas
│   ├── schemas.py        # Validação Pydantic
│   └── routers/
│       ├── clientes.py
│       ├── servicos.py
│       ├── agendamentos.py
│       └── relatorios.py
├── relatorios/           # PDFs gerados
├── requirements.txt
└── README.md
```

## 💡 Funcionalidades

- ✅ Cadastro e gestão de clientes
- ✅ Cadastro de serviços com duração e preço
- ✅ Agendamento com **validação automática de conflito de horário**
- ✅ Controle de status (agendado / concluído / cancelado)
- ✅ Registro de pagamentos (dinheiro, PIX, cartão)
- ✅ Relatório mensal em PDF com faturamento e estatísticas
