"""Chunking de documentos Markdown.

Corta primero por encabezados (#, ##, ...) y luego, dentro de cada
sección, agrupa párrafos completos hasta acercarse a un tamaño máximo
configurable — nunca por un número fijo de caracteres, que puede partir
una oración o una tabla de precios a la mitad y dañar la calidad del
retrieval. Entre chunks consecutivos de la misma sección se repite el
último párrafo del chunk anterior (overlap) para no perder contexto que
cae justo en el borde de un corte.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)

CountTokens = Callable[[str], int]


def _default_token_counter(text: str) -> int:
    # Aproximación simple (conteo de palabras), usada en tests y como
    # fallback: no depende de descargar ningún tokenizer. La ingesta real
    # pasa `embedding_provider.count_tokens`, que usa el tokenizer del
    # modelo de embeddings para un conteo preciso.
    return len(text.split())


@dataclass
class ChunkResult:
    heading_path: str
    content: str
    token_count: int
    content_hash: str


def _split_sections(body: str) -> list[tuple[str, str]]:
    """Parte el markdown en (heading_path, texto) por cada encabezado."""
    matches = list(_HEADING_RE.finditer(body))
    if not matches:
        stripped = body.strip()
        return [("", stripped)] if stripped else []

    sections: list[tuple[str, str]] = []
    open_headings: list[tuple[int, str]] = []  # (nivel, texto)

    intro = body[: matches[0].start()].strip()
    if intro:
        sections.append(("", intro))

    for i, match in enumerate(matches):
        level = len(match.group(1))
        heading_text = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_body = body[start:end].strip()

        while open_headings and open_headings[-1][0] >= level:
            open_headings.pop()
        open_headings.append((level, heading_text))
        heading_path = " > ".join(text for _, text in open_headings)

        if section_body:
            sections.append((heading_path, section_body))

    return sections


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _build_chunk(
    heading_path: str, paragraphs: list[str], count_tokens: CountTokens
) -> ChunkResult:
    text = "\n\n".join(paragraphs)
    return ChunkResult(
        heading_path=heading_path,
        content=text,
        token_count=count_tokens(text),
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


def chunk_markdown(
    content: str,
    max_tokens: int = 300,
    overlap_tokens: int = 40,
    count_tokens: CountTokens = _default_token_counter,
) -> list[ChunkResult]:
    chunks: list[ChunkResult] = []

    for heading_path, section_text in _split_sections(content):
        paragraphs = _split_paragraphs(section_text)
        buffer: list[str] = []
        buffer_tokens = 0

        for para in paragraphs:
            para_tokens = count_tokens(para)

            # Un párrafo más grande que max_tokens (p.ej. una tabla) se deja
            # como su propio chunk sobredimensionado en vez de partirlo a
            # ciegas a mitad de oración.
            if buffer and buffer_tokens + para_tokens > max_tokens:
                chunks.append(_build_chunk(heading_path, buffer, count_tokens))

                overlap = buffer[-1]
                if count_tokens(overlap) <= overlap_tokens:
                    buffer = [overlap]
                    buffer_tokens = count_tokens(overlap)
                else:
                    buffer = []
                    buffer_tokens = 0

            buffer.append(para)
            buffer_tokens += para_tokens

        if buffer:
            chunks.append(_build_chunk(heading_path, buffer, count_tokens))

    return chunks
