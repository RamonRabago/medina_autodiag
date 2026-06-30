"""
Pesos, umbrales y acciones estáticas del Dashboard V2 (Centro de Decisión ADMIN).

Toda calibración operativa vive aquí — no hardcodear en el router.
"""

from __future__ import annotations

# Orden de desempate entre familias (misma importancia relativa de score)
ORDEN_FAMILIAS: tuple[str, ...] = (
    "cobros",
    "entregas",
    "autorizaciones",
    "citas",
    "inventario",
    "caja",
)

# Peso base por familia (multiplicador principal del decision_score)
PESO_BASE_FAMILIA: dict[str, float] = {
    "cobros": 100.0,
    "entregas": 90.0,
    "autorizaciones": 85.0,
    "citas": 75.0,
    "inventario": 70.0,
    "caja": 65.0,
}

# Etiquetas humanas por familia
LABEL_FAMILIA: dict[str, str] = {
    "cobros": "Cobros pendientes",
    "entregas": "Listas para entrega",
    "autorizaciones": "Esperando autorización",
    "citas": "Citas operativas",
    "inventario": "Alertas de inventario",
    "caja": "Caja y turno",
}

# Rutas «ver todas» por familia
VER_TODAS_FAMILIA: dict[str, dict[str, str]] = {
    "cobros": {"to": "/operaciones/caja", "label": "Ver todos los cobros"},
    "entregas": {"to": "/operaciones/caja", "label": "Ver entregas pendientes"},
    "autorizaciones": {"to": "/operaciones/recepcion", "label": "Ver autorizaciones"},
    "citas": {"to": "/operaciones/recepcion", "label": "Ver citas"},
    "inventario": {"to": "/inventario", "label": "Ver inventario"},
    "caja": {"to": "/operaciones/caja", "label": "Ir a caja"},
}

# Ruta CTA por familia (ítem individual)
RUTA_FAMILIA: dict[str, str] = {
    "cobros": "/operaciones/caja",
    "entregas": "/operaciones/caja",
    "autorizaciones": "/operaciones/recepcion",
    "citas": "/operaciones/recepcion",
    "inventario": "/inventario",
    "caja": "/operaciones/caja",
}

# Factor antigüedad: (minutos_umbral_superior, multiplicador) ascendente
FACTORES_ANTIGUEDAD_MIN: tuple[tuple[float, float], ...] = (
    (30.0, 1.0),
    (120.0, 1.3),
    (300.0, 1.7),
    (float("inf"), 2.2),
)

# Factor proximidad (citas): minutos hasta el evento → multiplicador
FACTORES_PROXIMIDAD_MIN: tuple[tuple[float, float], ...] = (
    (60.0, 2.0),
    (240.0, 1.5),
    (1440.0, 1.2),
    (float("inf"), 1.0),
)

# Factor impacto por monto (MXN): (monto_umbral, multiplicador)
FACTORES_IMPACTO_MONTO: tuple[tuple[float, float], ...] = (
    (5000.0, 1.5),
    (2000.0, 1.3),
    (500.0, 1.15),
    (0.0, 1.0),
)

# decision_score → severidad ítem
UMBRALES_SEVERIDAD_ITEM: tuple[tuple[float, str], ...] = (
    (800.0, "critica"),
    (500.0, "alta"),
    (300.0, "media"),
    (100.0, "baja"),
    (0.0, "baja"),
)

# severidad_grupo: peor severidad entre ítems del grupo
SEVERIDAD_ORDEN: tuple[str, ...] = ("critica", "alta", "media", "baja")

# Máximo ítems visibles por grupo en prioridades_agrupadas
MAX_ITEMS_POR_GRUPO: int = 3

# Acciones frecuentes (estáticas, servidas desde backend)
ACCIONES_FRECUENTES: tuple[dict, ...] = (
    {"id": "recepcion", "label": "Recepción rápida", "to": "/operaciones/recepcion", "orden": 1},
    {"id": "caja", "label": "Caja operativa", "to": "/operaciones/caja", "orden": 2},
    {"id": "mi_taller", "label": "Mi Taller", "to": "/operaciones/mi-taller", "orden": 3},
    {"id": "citas", "label": "Citas", "to": "/citas", "orden": 4},
)

# Recomendación estable cuando no hay candidatos urgentes
RECOMENDACION_ESTABLE: dict = {
    "titulo": "Operación en orden",
    "accion_label": "Revisar Mi Taller",
    "to": "/operaciones/mi-taller",
    "severidad": "estable",
    "grupo": None,
    "decision_score": 0.0,
    "explicacion": ["No hay urgencias operativas pendientes en este momento."],
    "referencia": None,
}
