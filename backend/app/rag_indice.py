from . import db, embeddings


def _documentos() -> list[dict]:
    """Convierte cada destino, actividad y platillo ACTIVO en un texto autosuficiente."""
    docs = []

    for d in db.todos("SELECT * FROM destinos WHERE activo"):
        docs.append({
            "tabla": "destinos", "id": d["id"], "titulo": d["nombre"],
            "contenido": (
                f"Destino: {d['nombre']}. Departamento de {d['departamento']}, región {d['region']}. "
                f"Categoría: {d['categoria']}. {d['descripcion']} "
                f"Costo diario aproximado: Q{d['costo_diario_gtq']}. "
                f"Mejor época para ir: {d['mejor_epoca'] or 'todo el año'}."
            ),
        })

    for a in db.todos(
        """SELECT a.*, d.nombre AS destino FROM actividades a
           JOIN destinos d ON d.id = a.destino_id WHERE a.activo AND d.activo"""
    ):
        docs.append({
            "tabla": "actividades", "id": a["id"], "titulo": f"{a['nombre']} ({a['destino']})",
            "contenido": (
                f"Actividad en {a['destino']}: {a['nombre']}. Tipo: {a['tipo']}. {a['descripcion']} "
                f"Duración aproximada: {a['duracion_horas']} horas. Costo aproximado: Q{a['costo_gtq']}."
            ),
        })

    for p in db.todos("SELECT * FROM platillos WHERE activo"):
        docs.append({
            "tabla": "platillos", "id": p["id"], "titulo": p["nombre"],
            "contenido": (
                f"Platillo guatemalteco ({p['tipo']}): {p['nombre']}. Origen: {p['departamento_origen']}, "
                f"región {p['region']}. {p['descripcion']} Ingredientes: {p['ingredientes']}. "
                f"{'Es vegetariano.' if p['vegetariano'] else 'No es vegetariano.'}"
            ),
        })
    return docs


def reindexar() -> dict:
    """Recalcula los embeddings de todo y elimina los documentos de registros borrados o inactivos.
    Se puede ejecutar las veces que haga falta (usa UPSERT)."""
    docs = _documentos()
    vectores = embeddings.embed([d["contenido"] for d in docs])
    if vectores and len(vectores[0]) != 384:
        raise RuntimeError(f"El modelo produce {len(vectores[0])} dimensiones y la BD espera 384")

    for d, v in zip(docs, vectores):
        db.ejecutar(
            """INSERT INTO documentos_rag (fuente_tabla, fuente_id, titulo, contenido, embedding)
               VALUES (%s, %s, %s, %s, %s::vector)
               ON CONFLICT (fuente_tabla, fuente_id)
               DO UPDATE SET titulo = EXCLUDED.titulo, contenido = EXCLUDED.contenido,
                             embedding = EXCLUDED.embedding""",
            (d["tabla"], d["id"], d["titulo"], d["contenido"], embeddings.a_literal(v)),
        )

    # Limpieza: documentos cuyo registro original ya no existe o se desactivó
    vigentes = {(d["tabla"], d["id"]) for d in docs}
    eliminados = 0
    for fila in db.todos("SELECT id, fuente_tabla, fuente_id FROM documentos_rag"):
        if (fila["fuente_tabla"], fila["fuente_id"]) not in vigentes:
            db.ejecutar("DELETE FROM documentos_rag WHERE id = %s", (fila["id"],))
            eliminados += 1

    por_tabla = {t: sum(1 for d in docs if d["tabla"] == t) for t in ("destinos", "actividades", "platillos")}
    return {"indexados": len(docs), "eliminados": eliminados, **por_tabla}