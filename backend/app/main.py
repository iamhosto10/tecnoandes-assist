from fastapi import FastAPI

from app.api.ask import router as ask_router
from app.core.config import get_settings

app = FastAPI(title="TecnoAndes Assist API")
app.include_router(ask_router)


@app.get("/health")
def health() -> dict[str, str]:
    # Sin tocar la DB a propósito: separa "el proceso arrancó" de "la DB responde".
    # get_settings() sí se ejercita para detectar temprano un .env mal formado.
    get_settings()
    return {"status": "ok"}
