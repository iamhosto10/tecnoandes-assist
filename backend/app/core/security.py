"""Auth de la consola de revisión: un solo token compartido en `.env`
(`REVIEW_CONSOLE_TOKEN`). Es deliberadamente simple — alcanza para una
demo de portafolio donde hay un único "revisor". En producción esto sería
sesiones por usuario (OAuth/SSO) con roles y auditoría de quién hizo cada
acción, no un secreto compartido; ver docs/adr/.
"""

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def require_review_console_token(authorization: str = Header(default="")) -> None:
    settings = get_settings()
    expected = f"Bearer {settings.review_console_token}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de la consola de revisión inválido o ausente.",
        )
