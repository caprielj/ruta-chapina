from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from . import config, db

# Le dice a Swagger dónde hacer login y activa el botón "Authorize"
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hashear(password: str) -> str:
    """Convierte la contraseña en un hash bcrypt (bcrypt solo usa los primeros 72 bytes)."""
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verificar(password: str, hash_guardado: str) -> bool:
    """Compara una contraseña con el hash guardado."""
    try:
        return bcrypt.checkpw(password.encode()[:72], hash_guardado.encode())
    except ValueError:
        return False


def crear_token(usuario: dict) -> str:
    """Genera un JWT firmado con el id y el rol del usuario."""
    payload = {
        "sub": str(usuario["id"]),
        "rol": usuario["rol"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=config.JWT_HORAS),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITMO)


def usuario_actual(token: str = Depends(oauth2)) -> dict:
    """Dependencia: valida el token y devuelve el usuario. Se usa en todo endpoint protegido."""
    error = HTTPException(
        status_code=401,
        detail="Sesión inválida o expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        datos = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITMO])
        usuario_id = int(datos["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise error

    # Consultamos la BD en cada petición: así un usuario desactivado pierde el acceso al instante
    usuario = db.uno(
        "SELECT id, nombre, email, rol, activo, limite_tokens FROM usuarios WHERE id = %s",
        (usuario_id,),
    )
    if not usuario or not usuario["activo"]:
        raise error
    return usuario


def solo_admin(usuario: dict = Depends(usuario_actual)) -> dict:
    """Dependencia: deja pasar únicamente a administradores."""
    if usuario["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador puede hacer esto")
    return usuario