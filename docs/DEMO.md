# Guion de demo

~6 minutos. Necesita `make up`, `make migrate`, `make ingest`,
`ANTHROPIC_API_KEY` real en `.env`, y de preferencia `make seed-demo`
corrido antes (deja la cola con un caso de cada tipo).

## 0. Arranque (fuera de cámara)

```bash
make up && make migrate && make ingest
make seed-demo   # opcional pero recomendado: deja casos de ejemplo listos
make chat            # localhost:3000
make review-console  # localhost:3001
```

## 1. El chat — una respuesta directa (1 min)

En `localhost:3000`, preguntar algo bien cubierto por la base de
conocimiento: **"¿cuánto cuesta el iPhone 13?"**

- La respuesta llega directo, sin advertencia.
- Activar "modo transparente": mostrar los chunks recuperados con sus
  tres puntajes (vector, texto completo, RRF), las señales de confianza,
  y el cálculo del puntaje señal por señal. Este es el momento de explicar
  que el puntaje **no** se lo pregunté al modelo — se calcula del lado
  del sistema a partir de retrieval + lo que el modelo reporta de soporte.

## 2. El chat — una zona gris (1 min)

Preguntar algo donde la base tiene el producto pero no el detalle exacto:
**"¿el Samsung Galaxy S23 viene en azul?"**

- La respuesta se muestra, pero con advertencia (`warn`) — el modelo
  reportó `support=partial`: el producto existe, el color no está.

## 3. El chat — sin soporte y un reclamo (1 min)

- **"¿venden patinetas eléctricas?"** → no hay información, la respuesta
  genérica de respaldo, decisión `review`. Explicar: nunca se le muestra
  al cliente lo que el modelo "se inventó" cuando no hay soporte.
- **"me cobraron dos veces por la misma compra"** → decisión `escalate`,
  el mensaje reconoce la situación y promete seguimiento humano. Explicar
  la regla dura: un reclamo escala sin importar qué tan seguro esté el
  resto del sistema.

## 4. La consola de revisión — la cola (1.5 min)

En `localhost:3001` (token de `REVIEW_CONSOLE_TOKEN`):

- Mostrar la cola con los casos recién creados, filtros por motivo y
  confianza, atajos de teclado (`?` para verlos todos).
- Abrir el caso de la patineta: mostrar el desglose completo de señales y
  los chunks que sí se recuperaron (para explicar por qué no alcanzaron).
- Acción: **Corregir + crear documento** — redactar una respuesta corta
  y un documento nuevo sobre patinetas, enviar. Mostrar que el caso queda
  resuelto.
- Volver a `localhost:3000` y hacer la misma pregunta: ahora responde
  directo, citando el documento recién creado.

## 5. Brechas de conocimiento y dashboard (1 min)

- `/gaps`: si hay 2+ preguntas similares sin soporte, aparecen agrupadas
  con un botón "Crear documento" — la misma idea del paso anterior, pero
  a escala (detectando patrones, no casos aislados).
- `/dashboard`: distribución de decisiones, tamaño de la cola, costo y
  latencia acumulados, e historial de `make eval` si se corrió antes.

## 6. Cierre — calibración con datos (30 s)

Mencionar `make eval`: 25 casos con respuesta esperada, corridos contra
el pipeline real, midiendo recall@k, precisión de enrutamiento (¿escaló
los reclamos? ¿nunca escaló de más?) y el veredicto de un LLM juez — así
es como se ajustan los pesos de confianza, no a ojo.

## Notas para quien presenta

- Si algo no tiene `ANTHROPIC_API_KEY` configurada, `/ask` igual responde
  `200` con un mensaje de respaldo (decisión `review`) — es el
  comportamiento real ante una falla de la API, no un error de la demo.
- Los números de costo/latencia del dashboard son reales, de lo que se
  haya corrido en esa instancia — no están precalculados.
