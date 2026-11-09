from fastapi import APIRouter, Depends, HTTPException
from psycopg2 import errors, sql

from .. import db, seguridad
from ..schemas import UsuarioActualizar, UsuarioCrear, UsuarioSalida
from .auth import CONSULTA_USUARIO

# dependencies=[...] aplica "solo admin" a TODOS los endpoints de este router
router = APIRouter(
    prefix="/usuarios", tags=["Usuarios (admin)"],
    dependencies=[Depends(seguridad.solo_admin)],
)


@router.get("", response_model=list[UsuarioSalida])
def listar():
    return db.todos(CONSULTA_USUARIO + " ORDER BY u.id")


@router.get("/{usuario_id}", response_model=UsuarioSalida)
def ver(usuario_id: int):
    fila = db.uno(CONSULTA_USUARIO + " WHERE u.id = %s", (usuario_id,))
    if not fila:
        raise HTTPException(404, "Usuario no encontrado")
    return fila


@router.post("", response_model=UsuarioSalida, status_code=201)
def crear(datos: UsuarioCrear):
    try:
        nuevo = db.uno(
            """INSERT INTO usuarios (nombre, email, password_hash, rol, limite_tokens)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (datos.nombre, datos.email.lower(), seguridad.hashear(datos.password),
             datos.rol, datos.limite_tokens),
        )
    except errors.UniqueViolation:
        raise HTTPException(409, "Ya existe un usuario con ese correo")
    return db.uno(CONSULTA_USUARIO + " WHERE u.id = %s", (nuevo["id"],))


@router.put("/{usuario_id}", response_model=UsuarioSalida)
def editar(usuario_id: int, datos: UsuarioActualizar,
           admin: dict = Depends(seguridad.solo_admin)):
    # Solo los campos enviados (y no nulos)
    campos = {k: v for k, v in datos.model_dump(exclude_unset=True).items() if v is not None}
    if not campos:
        raise HTTPException(400, "No se envió ningún campo para actualizar")

    # El admin no puede quitarse a sí mismo el acceso (evita quedarse sin administradores)
    if usuario_id == admin["id"] and (campos.get("activo") is False or campos.get("rol") == "usuario"):
        raise HTTPException(400, "No puedes desactivarte ni quitarte el rol de admin a ti mismo")

    if "password" in campos:                        # la contraseña se guarda cifrada
        campos["password_hash"] = seguridad.hashear(campos.pop("password"))
    if "email" in campos:
        campos["email"] = campos["email"].lower()

    asignaciones = sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(c)) for c in campos)
    consulta = sql.SQL("UPDATE usuarios SET {a} WHERE id = %s RETURNING id").format(a=asignaciones)
    try:
        fila = db.uno(consulta, list(campos.values()) + [usuario_id])
    except errors.UniqueViolation:
        raise HTTPException(409, "Ya existe un usuario con ese correo")
    if not fila:
        raise HTTPException(404, "Usuario no encontrado")
    return db.uno(CONSULTA_USUARIO + " WHERE u.id = %s", (usuario_id,))


@router.delete("/{usuario_id}", status_code=204)
def borrar(usuario_id: int, admin: dict = Depends(seguridad.solo_admin)):
    if usuario_id == admin["id"]:
        raise HTTPException(400, "No puedes eliminar tu propia cuenta")
    # Borra también sus conversaciones y consumo (ON DELETE CASCADE en la BD)
    if db.ejecutar("DELETE FROM usuarios WHERE id = %s", (usuario_id,)) == 0:
        raise HTTPException(404, "Usuario no encontrado")