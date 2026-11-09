from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import db
from ..schemas import (ConsumoDetalle, ConsumoDia, ConsumoServicio, ConversacionDetalle,
                       ConversacionResumen, ResumenConsumo)
from ..seguridad import usuario_actual

router_historial = APIRouter(prefix="/historial", tags=["Historial"])
router_consumo = APIRouter(prefix="/consumo", tags=["Consumo de tokens"])

# Las fechas se comparan en hora de Guatemala, así el reporte web y Power BI cortan los días igual
ZONA = "America/Guatemala"


def _filtros(usuario, usuario_id, servicio_id, desde, hasta, alias, campo_fecha):
    """Arma la lista de condiciones SQL según los filtros recibidos.
    Regla de seguridad: un usuario normal SOLO puede ver sus propios datos;
    el administrador puede ver los de cualquiera o los de todos."""
    if usuario["rol"] != "admin":
        if usuario_id not in (None, usuario["id"]):
            raise HTTPException(403, "Solo puedes consultar tus propios datos")
        usuario_id = usuario["id"]
    if desde and hasta and desde > hasta:
        raise HTTPException(400, "La fecha 'desde' no puede ser posterior a 'hasta'")

    cond = []  # lista de (fragmento_sql, valor). Los fragmentos son fijos: el valor viaja como parámetro
    if usuario_id is not None:
        cond.append((f"{alias}.usuario_id = %s", usuario_id))
    if servicio_id is not None:
        cond.append((f"{alias}.servicio_id = %s", servicio_id))
    if desde:
        cond.append((f"({alias}.{campo_fecha} AT TIME ZONE '{ZONA}')::date >= %s", desde))
    if hasta:
        cond.append((f"({alias}.{campo_fecha} AT TIME ZONE '{ZONA}')::date <= %s", hasta))
    return cond


def _unir(cond, prefijo):
    """Convierte las condiciones en ' WHERE a AND b' (o ' AND a AND b') más su lista de parámetros."""
    if not cond:
        return "", []
    return prefijo + " AND ".join(f for f, _ in cond), [v for _, v in cond]


def _por_servicio(cond, servicio_id):
    """Consumo agrupado por servicio. LEFT JOIN: los servicios sin uso aparecen con ceros."""
    on_sql, params = _unir(cond, " AND ")
    donde = ""
    if servicio_id is not None:
        donde = " WHERE s.id = %s"
        params = params + [servicio_id]
    return db.todos(
        f"""SELECT s.id AS servicio_id, s.codigo, s.nombre AS servicio,
                   COUNT(c.id)::int AS consultas,
                   COALESCE(SUM(c.tokens_entrada), 0)::int AS tokens_entrada,
                   COALESCE(SUM(c.tokens_salida), 0)::int AS tokens_salida,
                   COALESCE(SUM(c.tokens_total), 0)::int AS tokens_total
            FROM servicios_ia s
            LEFT JOIN consumo_tokens c ON c.servicio_id = s.id{on_sql}
            {donde}
            GROUP BY s.id ORDER BY s.id""",
        params,
    )


# =====================================================================
# CONSUMO DE TOKENS
# =====================================================================
@router_consumo.get("/resumen", response_model=ResumenConsumo)
def resumen(usuario: dict = Depends(usuario_actual)):
    """Mi límite, lo que he consumido y lo que me queda, con el desglose por servicio."""
    cond = _filtros(usuario, usuario["id"], None, None, None, "c", "creado_en")
    por_servicio = _por_servicio(cond, None)
    usados = sum(f["tokens_total"] for f in por_servicio)
    return {
        "limite_tokens": usuario["limite_tokens"],
        "tokens_usados": usados,
        "tokens_restantes": max(usuario["limite_tokens"] - usados, 0),
        "consultas": sum(f["consultas"] for f in por_servicio),
        "por_servicio": por_servicio,
    }


@router_consumo.get("/por-servicio", response_model=list[ConsumoServicio])
def consumo_por_servicio(
    usuario_id: Optional[int] = Query(None, description="Solo el administrador puede usarlo"),
    servicio_id: Optional[int] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    usuario: dict = Depends(usuario_actual),
):
    """Consultas realizadas y consumo acumulado por servicio (reporte principal)."""
    cond = _filtros(usuario, usuario_id, servicio_id, desde, hasta, "c", "creado_en")
    return _por_servicio(cond, servicio_id)


@router_consumo.get("/por-dia", response_model=list[ConsumoDia])
def consumo_por_dia(
    usuario_id: Optional[int] = Query(None, description="Solo el administrador puede usarlo"),
    servicio_id: Optional[int] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    usuario: dict = Depends(usuario_actual),
):
    """Evolución diaria del consumo (para la gráfica de línea o barras)."""
    cond = _filtros(usuario, usuario_id, servicio_id, desde, hasta, "c", "creado_en")
    donde, params = _unir(cond, " WHERE ")
    return db.todos(
        f"""SELECT (c.creado_en AT TIME ZONE '{ZONA}')::date AS fecha,
                   COUNT(*)::int AS consultas,
                   COALESCE(SUM(c.tokens_entrada), 0)::int AS tokens_entrada,
                   COALESCE(SUM(c.tokens_salida), 0)::int AS tokens_salida,
                   COALESCE(SUM(c.tokens_total), 0)::int AS tokens_total
            FROM consumo_tokens c{donde}
            GROUP BY 1 ORDER BY 1""",
        params,
    )


@router_consumo.get("/detalle", response_model=list[ConsumoDetalle])
def consumo_detalle(
    usuario_id: Optional[int] = Query(None, description="Solo el administrador puede usarlo"),
    servicio_id: Optional[int] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    limite: int = Query(1000, ge=1, le=10000),
    desplazamiento: int = Query(0, ge=0),
    usuario: dict = Depends(usuario_actual),
):
    """Una fila por cada consulta realizada (tabla de detalle y fuente de datos de Power BI)."""
    cond = _filtros(usuario, usuario_id, servicio_id, desde, hasta, "c", "creado_en")
    donde, params = _unir(cond, " WHERE ")
    return db.todos(
        f"""SELECT c.id, (c.creado_en AT TIME ZONE '{ZONA}') AS fecha_hora,
                   c.usuario_id, u.nombre AS usuario, c.servicio_id, s.nombre AS servicio,
                   c.conversacion_id, c.tokens_entrada, c.tokens_salida, c.tokens_total
            FROM consumo_tokens c
            JOIN usuarios u ON u.id = c.usuario_id
            JOIN servicios_ia s ON s.id = c.servicio_id{donde}
            ORDER BY c.id DESC LIMIT %s OFFSET %s""",
        params + [limite, desplazamiento],
    )


# =====================================================================
# HISTORIAL DE CONVERSACIONES
# =====================================================================
BASE_CONVERSACIONES = """
    SELECT cv.id, cv.titulo, cv.servicio_id, s.nombre AS servicio,
           cv.usuario_id, u.nombre AS usuario, cv.creada_en,
           (SELECT COUNT(*) FROM mensajes m WHERE m.conversacion_id = cv.id)::int AS mensajes,
           COALESCE((SELECT SUM(c.tokens_total) FROM consumo_tokens c
                     WHERE c.conversacion_id = cv.id), 0)::int AS tokens_total
    FROM conversaciones cv
    JOIN servicios_ia s ON s.id = cv.servicio_id
    JOIN usuarios u ON u.id = cv.usuario_id
"""


@router_historial.get("", response_model=list[ConversacionResumen])
def listar_historial(
    usuario_id: Optional[int] = Query(None, description="Solo el administrador puede usarlo"),
    servicio_id: Optional[int] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    limite: int = Query(50, ge=1, le=500),
    desplazamiento: int = Query(0, ge=0),
    usuario: dict = Depends(usuario_actual),
):
    """Lista de conversaciones. El usuario ve las suyas; el admin ve las de todos (o filtra por usuario)."""
    cond = _filtros(usuario, usuario_id, servicio_id, desde, hasta, "cv", "creada_en")
    donde, params = _unir(cond, " WHERE ")
    return db.todos(
        BASE_CONVERSACIONES + donde + " ORDER BY cv.id DESC LIMIT %s OFFSET %s",
        params + [limite, desplazamiento],
    )


@router_historial.get("/{conversacion_id}", response_model=ConversacionDetalle)
def ver_conversacion(conversacion_id: int, usuario: dict = Depends(usuario_actual)):
    """Una conversación con todos sus mensajes y las fuentes citadas."""
    conv = db.uno(BASE_CONVERSACIONES + " WHERE cv.id = %s", (conversacion_id,))
    # Si no es suya respondemos 404 (no 403): no revelamos que existe
    if not conv or (usuario["rol"] != "admin" and conv["usuario_id"] != usuario["id"]):
        raise HTTPException(404, "Conversación no encontrada")
    mensajes = db.todos(
        "SELECT id, rol, contenido, fuentes, creado_en FROM mensajes WHERE conversacion_id = %s ORDER BY id",
        (conversacion_id,),
    )
    return {**conv, "lista_mensajes": mensajes}