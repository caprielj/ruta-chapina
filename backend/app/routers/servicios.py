from fastapi import APIRouter, Depends, HTTPException
from psycopg2 import sql

from .. import db
from ..schemas import ServicioActualizar, ServicioSalida
from ..seguridad import solo_admin, usuario_actual

router = APIRouter(prefix="/servicios", tags=["Servicios de IA"])


@router.get("", response_model=list[ServicioSalida])
def listar(usuario: dict = Depends(usuario_actual)):
    """El admin ve todos los servicios; el usuario solo los activos."""
    if usuario["rol"] == "admin":
        return db.todos("SELECT id, codigo, nombre, descripcion, activo FROM servicios_ia ORDER BY id")
    return db.todos(
        "SELECT id, codigo, nombre, descripcion, activo FROM servicios_ia WHERE activo ORDER BY id"
    )


@router.put("/{servicio_id}", response_model=ServicioSalida)
def actualizar(servicio_id: int, datos: ServicioActualizar, _admin: dict = Depends(solo_admin)):
    """El admin activa/desactiva un servicio o cambia su nombre y descripción."""
    campos = {k: v for k, v in datos.model_dump(exclude_unset=True).items() if v is not None}
    if not campos:
        raise HTTPException(400, "No se envió ningún campo para actualizar")
    asignaciones = sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(c)) for c in campos)
    consulta = sql.SQL(
        "UPDATE servicios_ia SET {a} WHERE id = %s RETURNING id, codigo, nombre, descripcion, activo"
    ).format(a=asignaciones)
    fila = db.uno(consulta, list(campos.values()) + [servicio_id])
    if not fila:
        raise HTTPException(404, "Servicio no encontrado")
    return fila