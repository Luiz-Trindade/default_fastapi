# default_fastapi

Projeto base para APIs **FastAPI** com suporte a CRUD, cache e controle de concorrência usando **asyncio.Semaphore**.

---

## 💡 Funcionalidades

- CRUD completo para recursos (ex: Users) usando **SQLModel + SQLite**.
- Cache persistente em disco usando **DiskCache**.
- Controle de concorrência com **asyncio.Semaphore** para limitar requisições simultâneas.
- Estrutura modular e pronta para escalabilidade.
- Processamento de requisições assíncronas seguro e eficiente.

---

## ⚡ Tecnologias

- **Python 3.11+**
- **FastAPI**
- **SQLModel / SQLAlchemy**
- **SQLite**
- **DiskCache**
- **asyncio** (Semaphore para limitar concorrência)

---

## 🏗️ Estrutura de diretórios

```

default_fastapi/
├── app/
│   ├── main.py          # Inicialização do FastAPI
│   ├── config.py        # Configurações do banco e cache
│   ├── models/          # Models SQLModel
│   ├── routers/         # Endpoints
│   └── utils/           # Funções auxiliares
├── requirements.txt
└── README.md

```

---

## 🚀 Como rodar

1. Clonar o repositório:
```bash
git clone <repo-url>
cd default_fastapi
```

2. Criar ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

3. Instalar dependências:

```bash
pip install -r requirements.txt
```

4. Rodar o servidor:

```bash
uvicorn app.main:app --reload
```

O servidor estará disponível em: `http://127.0.0.1:8000`

---

## 🔧 Configurações

* **Banco de dados**: `config.py` (atualmente SQLite, pode trocar para PostgreSQL ou MySQL).
* **Cache**: `DiskCache` persistente em `./cache`.
* **Limite de concorrência**: definido via `asyncio.Semaphore(cpu_count())` no router.

---

## 📝 Notas

* Este projeto serve como **template rápido** para iniciar APIs FastAPI robustas e escaláveis.
* Todas as rotas respeitam **limite de concorrência**, protegendo o servidor de sobrecarga em picos de tráfego.

---

## 📌 Contato

Desenvolvido por Luiz Trindade – **programador fullstack**.
