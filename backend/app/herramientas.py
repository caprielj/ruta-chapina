import logging
import math

import httpx

from . import db, embeddings

# =====================================================================
# Utilidades internas
# =====================================================================
def _ids(valores, maximo: int) -> list[int]:
    """Convierte a enteros, quita repetidos (conservando el orden) y limita la cantidad."""
    vistos = []
    for v in valores or []:
        v = int(v)
        if v not in vistos:
            vistos.append(v)
    return vistos[:maximo]


def _destinos_por_id(ids: list[int]) -> list[dict]:
    """Destinos activos, en el mismo orden en que se pidieron."""
    if not ids:
        return []
    filas = db.todos(
        """SELECT id, nombre, departamento, categoria, costo_diario_gtq, mejor_epoca, latitud, longitud
           FROM destinos WHERE id = ANY(%s) AND activo""",
        (ids,),
    )
    por_id = {f["id"]: f for f in filas}
    return [por_id[i] for i in ids if i in por_id]


def _basico(d: dict) -> dict:
    """Formato compacto de un destino. lat/lon (float) son para el mapa de la web;
    se quitan antes de enviar al modelo para ahorrar tokens."""
    return {
        "id": d["id"], "nombre": d["nombre"], "departamento": d["departamento"],
        "categoria": d["categoria"], "costo_diario_gtq": d["costo_diario_gtq"],
        "mejor_epoca": d["mejor_epoca"],
        "lat": float(d["latitud"]), "lon": float(d["longitud"]),
    }


def _haversine(lat1, lon1, lat2, lon2) -> float:
    """Distancia en línea recta (km) entre dos coordenadas."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# =====================================================================
# Herramientas
# =====================================================================
def buscar_destinos(consulta: str, presupuesto_diario_max: int | None = None, max_resultados: int = 4) -> dict:
    """Busca destinos por significado (búsqueda vectorial) y, opcionalmente, por costo diario."""
    max_resultados = max(1, min(int(max_resultados or 4), 6))
    tope = int(presupuesto_diario_max) if presupuesto_diario_max else None
    vector = embeddings.a_literal(embeddings.embed_uno(consulta))
    filas = db.todos(
        """SELECT d.id, d.nombre, d.departamento, d.categoria, d.costo_diario_gtq,
                  d.mejor_epoca, d.latitud, d.longitud
           FROM documentos_rag r JOIN destinos d ON d.id = r.fuente_id
           WHERE r.fuente_tabla = 'destinos' AND d.activo
             AND (%s::int IS NULL OR d.costo_diario_gtq <= %s::int)
           ORDER BY r.embedding <=> %s::vector
           LIMIT %s""",
        (tope, tope, vector, max_resultados),
    )
    if not filas:
        return {"destinos": [], "nota": "Ningún destino cumple ese presupuesto o criterio"}
    return {"destinos": [_basico(f) for f in filas]}


def detalle_destinos(destino_ids: list[int]) -> dict:
    """Actividades (con duración y costo) y platillos típicos de hasta 4 destinos."""
    resultado = []
    for d in _destinos_por_id(_ids(destino_ids, 4)):
        actividades = db.todos(
            """SELECT id, nombre, tipo, duracion_horas, costo_gtq FROM actividades
               WHERE destino_id = %s AND activo ORDER BY id LIMIT 6""",
            (d["id"],),
        )
        platillos = db.todos(
            "SELECT nombre FROM platillos WHERE activo AND departamento_origen = %s ORDER BY id LIMIT 3",
            (d["departamento"],),
        )
        item = _basico(d)
        item["actividades"] = [
            {"id": a["id"], "nombre": a["nombre"], "tipo": a["tipo"],
             "horas": float(a["duracion_horas"]), "costo_gtq": a["costo_gtq"]}
            for a in actividades
        ]
        item["platillos_tipicos"] = [p["nombre"] for p in platillos]
        resultado.append(item)
    return {"destinos": resultado}


def consultar_clima(destino_ids: list[int], dias: int = 3) -> dict:
    """Pronóstico real desde Open-Meteo (gratis, sin clave) para cada destino."""
    dias = max(1, min(int(dias or 3), 7))
    salida = []
    with httpx.Client(timeout=8) as http:
        for d in _destinos_por_id(_ids(destino_ids, 4)):
            try:
                r = http.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": float(d["latitud"]), "longitude": float(d["longitud"]),
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
                        "timezone": "America/Guatemala", "forecast_days": dias,
                    },
                )
                r.raise_for_status()
                j = r.json()["daily"]
                salida.append({
                    "destino_id": d["id"], "destino": d["nombre"],
                    "dias": [
                        {"fecha": j["time"][i], "max": j["temperature_2m_max"][i],
                         "min": j["temperature_2m_min"][i],
                         "lluvia_pct": j["precipitation_probability_max"][i],
                         "mm": j["precipitation_sum"][i]}
                        for i in range(len(j["time"]))
                    ],
                })
            except Exception:
                logging.exception("Fallo consultando Open-Meteo")
                # No lanzamos error: el agente debe poder seguir y avisar que no hubo clima
                salida.append({"destino_id": d["id"], "destino": d["nombre"],
                               "error": "No se pudo consultar el clima ahora"})
    return {"clima": salida}


def calcular_distancia(destino_ids: list[int]) -> dict:
    """Distancia y tiempo por carretera entre destinos consecutivos (OSRM; si falla, estimación)."""
    destinos = _destinos_por_id(_ids(destino_ids, 5))
    if len(destinos) < 2:
        return {"error": "Se necesitan al menos 2 destinos válidos"}
    tramos = []
    with httpx.Client(timeout=8) as http:
        for a, b in zip(destinos, destinos[1:]):
            la1, lo1, la2, lo2 = float(a["latitud"]), float(a["longitud"]), float(b["latitud"]), float(b["longitud"])
            try:
                r = http.get(
                    f"https://router.project-osrm.org/route/v1/driving/{lo1},{la1};{lo2},{la2}",
                    params={"overview": "false"},
                )
                r.raise_for_status()
                ruta = r.json()["routes"][0]
                km, horas, fuente = ruta["distance"] / 1000, ruta["duration"] / 3600, "OSRM (carretera)"
            except Exception:
                # Plan B: línea recta x 1.4 (curvas) a 40 km/h (carreteras de montaña)
                km = _haversine(la1, lo1, la2, lo2) * 1.4
                horas, fuente = km / 40, "estimación"
            tramos.append({"origen": a["nombre"], "destino": b["nombre"],
                           "km": round(km), "horas": round(horas, 1), "fuente": fuente})
    return {"tramos": tramos}


def calcular_presupuesto(personas: int, tramos: list[dict]) -> dict:
    """Presupuesto en quetzales: (costo diario x días x personas) + actividades elegidas.
    Hacemos la aritmética aquí, no en el modelo, para que las cifras sean exactas."""
    personas = max(1, int(personas or 1))
    detalle, total = [], 0
    for t in (tramos or [])[:5]:
        destinos = _destinos_por_id([int(t["destino_id"])])
        if not destinos:
            continue
        d = destinos[0]
        dias = max(1, int(t.get("dias", 1)))
        base = d["costo_diario_gtq"] * dias * personas
        ids_act = _ids(t.get("actividad_ids"), 10)
        acts = db.todos(
            "SELECT nombre, costo_gtq FROM actividades WHERE id = ANY(%s) AND destino_id = %s AND activo",
            (ids_act, d["id"]),
        ) if ids_act else []
        costo_acts = sum(a["costo_gtq"] for a in acts) * personas
        subtotal = base + costo_acts
        total += subtotal
        detalle.append({
            "destino": d["nombre"], "dias": dias,
            "alojamiento_comida_gtq": base, "actividades_gtq": costo_acts,
            "actividades": [a["nombre"] for a in acts], "subtotal_gtq": subtotal,
        })
    return {
        "personas": personas, "tramos": detalle, "total_gtq": total,
        "por_persona_gtq": round(total / personas),
        "nota": "Montos aproximados; no incluyen transporte entre destinos.",
    }


# =====================================================================
# Catálogo que se le presenta al modelo (formato de "function calling")
# =====================================================================
def _def(nombre: str, descripcion: str, propiedades: dict, requeridos: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": nombre, "description": descripcion,
        "parameters": {"type": "object", "properties": propiedades, "required": requeridos},
    }}


ESQUEMAS = {
    "buscar_destinos": _def(
        "buscar_destinos", "Busca destinos de Guatemala por intereses (volcanes, playa, cultura, comida...).",
        {"consulta": {"type": "string", "description": "Intereses o tema en español"},
         "presupuesto_diario_max": {"type": "integer", "description": "Costo diario máximo por persona en Q"},
         "max_resultados": {"type": "integer"}},
        ["consulta"]),
    "detalle_destinos": _def(
        "detalle_destinos", "Actividades (ids, duración, costo) y platillos típicos de destinos.",
        {"destino_ids": {"type": "array", "items": {"type": "integer"}}}, ["destino_ids"]),
    "consultar_clima": _def(
        "consultar_clima", "Pronóstico real de los próximos días (1 a 7) para destinos.",
        {"destino_ids": {"type": "array", "items": {"type": "integer"}},
         "dias": {"type": "integer"}}, ["destino_ids"]),
    "calcular_distancia": _def(
        "calcular_distancia", "Km y horas por carretera entre destinos, en el orden dado.",
        {"destino_ids": {"type": "array", "items": {"type": "integer"}}}, ["destino_ids"]),
    "calcular_presupuesto": _def(
        "calcular_presupuesto", "Presupuesto total en Q. Un tramo por destino, con días y ids de actividades.",
        {"personas": {"type": "integer"},
         "tramos": {"type": "array", "items": {"type": "object", "properties": {
             "destino_id": {"type": "integer"}, "dias": {"type": "integer"},
             "actividad_ids": {"type": "array", "items": {"type": "integer"}}},
             "required": ["destino_id", "dias"]}}},
        ["personas", "tramos"]),
}

EJECUTORES = {
    "buscar_destinos": buscar_destinos, "detalle_destinos": detalle_destinos,
    "consultar_clima": consultar_clima, "calcular_distancia": calcular_distancia,
    "calcular_presupuesto": calcular_presupuesto,
}


def ejecutar(nombre: str, argumentos: dict) -> dict:
    """Ejecuta una herramienta pedida por el modelo. Nunca lanza error: si algo falla devuelve
    {"error": ...} para que el modelo pueda corregir o avisar al usuario."""
    funcion = EJECUTORES.get(nombre)
    if funcion is None:
        return {"error": f"La herramienta '{nombre}' no existe"}
    try:
        return funcion(**argumentos)
    except Exception:
        logging.exception("Falló la herramienta %s", nombre)
        return {"error": "Argumentos inválidos o fallo al ejecutar la herramienta"}