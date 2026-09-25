# 0001 — Retrieval híbrido en SQL crudo, fusionado con RRF en Python

## Estado

Aceptado (Fase 1).

## Contexto

El retrieval necesita combinar dos señales muy distintas — similitud vectorial
(pgvector, coseno) y texto completo en español (`tsvector` + `unaccent`) —
en un solo ranking. El resto del proyecto usa SQLAlchemy 2 (ORM + Alembic)
para CRUD y modelos.

## Decisión

La consulta de retrieval se escribe con `sqlalchemy.text()` (SQL crudo
parametrizado), no con el query builder del ORM: dos `SELECT` simples e
independientes (uno por similitud vectorial, otro por `ts_rank`), cada uno
fácil de correr a mano con `EXPLAIN` o `make search` por separado.

La fusión de los dos rankings se hace en **Python puro**
(`reciprocal_rank_fusion` en `app/rag/retrieval.py`), no en un tercer CTE de
SQL: `score = sum(1 / (k + rank))` sobre la POSICIÓN de cada chunk en cada
lista, no sobre los puntajes crudos. Se prefiere RRF sobre sumar los
puntajes directamente porque la similitud coseno (0–1) y `ts_rank` (una
escala arbitraria que depende de la frecuencia de términos del corpus) no
son comparables entre sí — sumarlos le daría más peso al método que "por
casualidad" produce números más grandes.

## Consecuencias

- Cada mitad del retrieval se puede depurar, testear y ajustar por
  separado; `reciprocal_rank_fusion` se testea sin base de datos
  (`tests/unit/test_rrf.py`).
- El SQL es legible como SQL, no reconstruido a través de un query builder
  — es justo la pieza que más se debuggea en un RAG.
- Costo: un CTE único hubiera sido una sola ida a la base en vez de dos; a
  la escala de esta demo (cientos de chunks) esa diferencia no es medible.

## Alternativas consideradas

- **Un solo CTE con RRF en SQL.** Más "elegante" en el sentido de una sola
  consulta, pero opaco para depurar y difícil de testear sin una base de
  datos levantada.
- **Sumar los puntajes crudos en vez de RRF.** Descartado por el problema
  de escalas descrito arriba.
