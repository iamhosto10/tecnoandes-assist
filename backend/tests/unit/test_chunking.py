from app.rag.chunking import chunk_markdown


def test_splits_by_heading_and_keeps_heading_path():
    content = (
        "# Título\n\n"
        "## Sección A\n\nContenido de la sección A.\n\n"
        "## Sección B\n\nContenido de la sección B."
    )

    chunks = chunk_markdown(content, max_tokens=100)

    assert [c.heading_path for c in chunks] == ["Título > Sección A", "Título > Sección B"]
    assert "sección A" in chunks[0].content
    assert "sección B" in chunks[1].content


def test_groups_paragraphs_until_max_tokens():
    # 3 párrafos cortos de 5 palabras cada uno; con max_tokens=8 no caben
    # dos juntos, así que cada uno debería terminar en su propio chunk.
    paragraphs = ["una dos tres cuatro cinco"] * 3
    content = "## Sección\n\n" + "\n\n".join(paragraphs)

    chunks = chunk_markdown(content, max_tokens=8, overlap_tokens=0)

    assert len(chunks) == 3
    assert all(c.heading_path == "Sección" for c in chunks)


def test_overlap_repeats_last_paragraph_in_next_chunk():
    paragraphs = ["parrafo uno con contenido", "parrafo dos con contenido", "parrafo tres final"]
    content = "## Sección\n\n" + "\n\n".join(paragraphs)

    # max_tokens fuerza un corte entre cada párrafo; overlap_tokens grande
    # para que siempre quepa como inicio del siguiente chunk.
    chunks = chunk_markdown(content, max_tokens=5, overlap_tokens=10)

    assert len(chunks) >= 2
    assert paragraphs[0] in chunks[0].content
    assert paragraphs[0] in chunks[1].content  # se repite como overlap


def test_no_headings_produces_single_section():
    content = "Solo un párrafo suelto, sin encabezados en el documento."

    chunks = chunk_markdown(content, max_tokens=100)

    assert len(chunks) == 1
    assert chunks[0].heading_path == ""


def test_content_hash_is_deterministic_and_content_specific():
    content = "## Sección\n\nTexto A."

    chunks_a = chunk_markdown(content, max_tokens=100)
    chunks_b = chunk_markdown(content, max_tokens=100)
    chunks_c = chunk_markdown("## Sección\n\nTexto B.", max_tokens=100)

    assert chunks_a[0].content_hash == chunks_b[0].content_hash
    assert chunks_a[0].content_hash != chunks_c[0].content_hash


def test_empty_content_produces_no_chunks():
    assert chunk_markdown("", max_tokens=100) == []
    assert chunk_markdown("   \n\n  ", max_tokens=100) == []
