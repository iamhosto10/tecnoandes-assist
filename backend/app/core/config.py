from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Un solo .env en la raíz del repo (ver .env.example), no uno por app.
# Dentro de Docker las variables ya llegan por `environment`/`env_file` de
# Compose, así que esta ruta simplemente no existe y pydantic-settings cae
# de vuelta a las variables de entorno reales del proceso.
_REPO_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Configuración de la app, leída de variables de entorno / .env.

    Todo lo que pueda variar entre entornos o necesitar calibración
    (pesos de confianza, umbrales, modelo) vive aquí, nunca hardcodeado
    en el código de negocio.
    """

    model_config = SettingsConfigDict(env_file=_REPO_ROOT_ENV, extra="ignore")

    # Base de datos
    database_url: str = "postgresql+psycopg://tecnoandes:change-me@localhost:5432/tecnoandes"

    # LLM
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    # USD por millón de tokens (Claude Haiku 4.5, precios publicados de Anthropic).
    # Aquí, no hardcodeado en generation.py, para poder actualizarlos sin tocar código.
    anthropic_input_price_per_mtok: float = 1.00
    anthropic_output_price_per_mtok: float = 5.00

    # Embeddings
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dimensions: int = 384

    # Retrieval
    retrieval_top_k: int = 5
    reranker_enabled: bool = False

    # Confianza: pesos (deben sumar ~1.0) y umbrales de enrutamiento.
    # Son una heurística inicial que se recalibra con `make eval` (ver Fase 6).
    confidence_threshold_low: int = 40
    confidence_threshold_high: int = 75
    confidence_weight_retrieval_score: float = 0.5
    confidence_weight_retrieval_margin: float = 0.15
    confidence_weight_support: float = 0.35
    # "Valores de referencia" para normalizar retrieval_score/margin antes de
    # ponderarlos: con E5 la similitud coseno cruda vive en un rango angosto
    # (~0.75-0.90 en nuestra base, visto con `make search`), así que usarla
    # tal cual como score 0-100 estaría mal calibrado. floor/ceiling mapean
    # ese rango observado a 0-1; se ajustan con `make eval`.
    confidence_retrieval_floor: float = 0.75
    confidence_retrieval_ceiling: float = 0.90
    confidence_margin_ceiling: float = 0.05

    # Consola de revisión (auth simple de un solo token; ver docs/adr)
    review_console_token: str = "change-me-too"

    # App
    log_level: str = "INFO"
    backend_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
