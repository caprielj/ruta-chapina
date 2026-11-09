from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2 import errors, sql

from . import db
from .seguridad import solo_admin, usuario_actual


def _error_http(e: Exception) -> HTTPException:
    """Traduce errores de la BD a respuestas HTTP entendibles."""
    if isinstance(e, errors.UniqueViolation):
        return HTTPException(409, "Ya existe un registro con ese valor único")
    return HTTPException(400, "Referencia a un registro que no existe")


def crear_router_crud(prefijo: str, tabla: str, Entrada, Salida, etiqueta: str) -> APIRouter:
    """Crea los 5 endpoints (listar, ver, crear, editar, borrar) para una tabla.
    - Cualquier usuario autenticado puede LEER (pero solo ve registros activos).
    - Solo el administrador puede CREAR, EDITAR y BORRAR."""
    router = APIRouter(prefix=prefijo, tags=[etiqueta])
    # Las columnas salen del modelo Pydantic (código nuestro), nunca de lo que envíe el cliente
    columnas = list(Entrada.model_fields.keys())
    t = sql.Identifier(tabla)
    cols = sql.SQL(", ").join(sql.Identifier(c) for c in columnas)

    @router.get("", response_model=list[Salida])
    def listar(
        q: Optional[str] = Query(None, description="Buscar por nombre"),
        limite: int = Query(100, ge=1, le=500),
        desplazamiento: int = Query(0, ge=0),
        usuario: dict = Depends(usuario_actual),
    ):
        condiciones, params = [], []
        if usuario["rol"] != "admin":
            condiciones.append(sql.SQL("activo = TRUE"))
        if q and "nombre" in columnas:
            condiciones.append(sql.SQL("nombre ILIKE %s"))
            params.append(f"%{q}%")
        donde = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(condiciones) if condiciones else sql.SQL("")
        consulta = sql.SQL("SELECT id, {c} FROM {t}{w} ORDER BY id LIMIT %s OFFSET %s").format(
            c=cols, t=t, w=donde
        )
        return db.todos(consulta, params + [limite, desplazamiento])

    @router.get("/{registro_id}", response_model=Salida)
    def ver(registro_id: int, usuario: dict = Depends(usuario_actual)):
        extra = sql.SQL("") if usuario["rol"] == "admin" else sql.SQL(" AND activo = TRUE")
        consulta = sql.SQL("SELECT id, {c} FROM {t} WHERE id = %s{e}").format(c=cols, t=t, e=extra)
        fila = db.uno(consulta, (registro_id,))
        if not fila:
            raise HTTPException(404, "No encontrado")
        return fila

    @router.post("", response_model=Salida, status_code=201)
    def crear(datos: Entrada, _admin: dict = Depends(solo_admin)):
        marcadores = sql.SQL(", ").join([sql.Placeholder()] * len(columnas))
        consulta = sql.SQL("INSERT INTO {t} ({c}) VALUES ({v}) RETURNING id, {c}").format(
            t=t, c=cols, v=marcadores
        )
        try:
            return db.uno(consulta, [getattr(datos, c) for c in columnas])
        except (errors.UniqueViolation, errors.ForeignKeyViolation) as e:
            raise _error_http(e)

    @router.put("/{registro_id}", response_model=Salida)
    def editar(registro_id: int, datos: Entrada, _admin: dict = Depends(solo_admin)):
        asignaciones = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(c)) for c in columnas
        )
        consulta = sql.SQL("UPDATE {t} SET {a} WHERE id = %s RETURNING id, {c}").format(
            t=t, a=asignaciones, c=cols
        )
        try:
            fila = db.uno(consulta, [getattr(datos, c) for c in columnas] + [registro_id])
        except (errors.UniqueViolation, errors.ForeignKeyViolation) as e:
            raise _error_http(e)
        if not fila:
            raise HTTPException(404, "No encontrado")
        return fila

    @router.delete("/{registro_id}", status_code=204)
    def borrar(registro_id: int, _admin: dict = Depends(solo_admin)):
        consulta = sql.SQL("DELETE FROM {t} WHERE id = %s").format(t=t)
        if db.ejecutar(consulta, (registro_id,)) == 0:
            raise HTTPException(404, "No encontrado")

    return router