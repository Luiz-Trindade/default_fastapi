from os import cpu_count
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routes.user import router as user_router
import time

app = FastAPI(
    title="Minha API de Usuários",
    description="""
API construída com FastAPI e SQLModel.

- CRUD de usuários
- Estrutura mínima escalável
- Middleware de logging e CORS
""",
    version="1.0.0",
    contact={
        "name": "Luiz",
        "email": "luiz@email.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

API_PREFIX = "/api/v1"

# Logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    print(f"{request.method} {request.url} completed_in={process_time:.2f}ms status_code={response.status_code}")
    return response

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(user_router, prefix=f"{API_PREFIX}/users")

@app.get(API_PREFIX + "/", tags=["Root"])
def root():
    """
    Rota raiz da API
    """
    return {"message": "Hello, World!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8100, workers=cpu_count())
