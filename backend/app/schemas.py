from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Autenticación ----------
class TokenSalida(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str


# ---------- Usuarios ----------
class UsuarioCrear(BaseModel):
    nombre: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    rol: Literal["admin", "usuario"] = "usuario"
    limite_tokens: int = Field(default=20000, ge=0)


class UsuarioActualizar(BaseModel):
    # Todo es opcional: solo se cambia lo que se envíe
    nombre: Optional[str] = Field(default=None, min_length=2)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)
    rol: Optional[Literal["admin", "usuario"]] = None
    activo: Optional[bool] = None
    limite_tokens: Optional[int] = Field(default=None, ge=0)


class UsuarioSalida(BaseModel):
    id: int
    nombre: str
    email: str
    rol: str
    activo: bool
    limite_tokens: int
    tokens_usados: int = 0
    creado_en: datetime


# ---------- Servicios de IA ----------
class ServicioSalida(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    activo: bool


class ServicioActualizar(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2)
    descripcion: Optional[str] = None
    activo: Optional[bool] = None


# ---------- Destinos ----------
class DestinoIn(BaseModel):
    nombre: str = Field(min_length=2)
    departamento: str
    region: str
    categoria: str
    descripcion: str
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    costo_diario_gtq: int = Field(ge=0)
    mejor_epoca: Optional[str] = None
    imagen_url: Optional[str] = None
    activo: bool = True


class DestinoOut(DestinoIn):
    id: int


# ---------- Actividades ----------
class ActividadIn(BaseModel):
    destino_id: int
    nombre: str = Field(min_length=2)
    tipo: str
    descripcion: str
    duracion_horas: float = Field(ge=0)
    costo_gtq: int = Field(default=0, ge=0)
    activo: bool = True


class ActividadOut(ActividadIn):
    id: int


# ---------- Platillos ----------
class PlatilloIn(BaseModel):
    nombre: str = Field(min_length=2)
    tipo: str
    departamento_origen: str
    region: str
    descripcion: str
    ingredientes: str
    vegetariano: bool = False
    activo: bool = True


class PlatilloOut(PlatilloIn):
    id: int