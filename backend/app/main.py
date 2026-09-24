from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ask import router as ask_router
from app.api.documents import router as documents_router
from app.api.review import router as review_router
from app.core.config import get_settings

app = FastAPI(title="TecnoAndes Assist API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ask_router)
app.include_router(review_router)
app.include_router(documents_router)


@app.get("/health")
def health() -> dict[str, str]:
    # Sin tocar la DB a propósito: separa "el proceso arrancó" de "la DB responde".
    # get_settings() sí se ejercita para detectar temprano un .env mal formado.
    get_settings()
    return {"status": "ok"}
