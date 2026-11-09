from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from .. import db, seguridad
from ..schemas import TokenSalida, UsuarioSalida

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# Consulta que devuelve al usuario junto con los tokens que lleva consumidos
CONSULTA_USUARIO = """
    SELECT u.id, u.nombre, u.email, u.rol, u.activo, u.limite_tokens, u.creado_en,
           COALESCE((SELECT SUM(c.tokens_total) FROM consumo_tokens c
                     WHERE c.usuario_id = u.id), 0)::int AS tokens_usados
    FROM usuarios u
"""


@router.post("/login", response_model=TokenSalida)
def login(form: OAuth2PasswordRequestForm = Depends()):
    """Inicio de sesión. En el campo 'username' va el correo electrónico."""
    usuario = db.uno(
        "SELECT id, nombre, email, password_hash, rol, activo FROM usuarios WHERE email = %s",
        (form.username.strip().lower(),),
    )
    # Mismo mensaje para todos los fallos: no revelamos si el correo existe
    if not usuario or not usuario["activo"] or not seguridad.verificar(
        form.password, usuario["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": seguridad.crear_token(usuario),
        "token_type": "bearer",
        "rol": usuario["rol"],
        "nombre": usuario["nombre"],
    }


@router.post("/logout")
def logout(_usuario: dict = Depends(seguridad.usuario_actual)):
    """Cierre de sesión. El JWT no se guarda en el servidor, así que el cierre real
    consiste en que el cliente (frontend) descarte su token."""
    return {"mensaje": "Sesión cerrada. Descarta el token en el cliente."}


@router.get("/yo", response_model=UsuarioSalida)
def mi_perfil(usuario: dict = Depends(seguridad.usuario_actual)):
    """Datos del usuario con sesión iniciada y sus tokens consumidos."""
    return db.uno(CONSULTA_USUARIO + " WHERE u.id = %s", (usuario["id"],))