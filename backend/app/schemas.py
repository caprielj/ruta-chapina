from datetime import date, datetime
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



# ---------- Chatbot ----------
class ChatEntrada(BaseModel):
    mensaje: str = Field(min_length=1, max_length=1000)
    # Si se omite, se abre una conversación nueva; si se envía, se continúa esa
    conversacion_id: Optional[int] = None


class Fuente(BaseModel):
    tabla: str       # destinos | actividades | platillos
    id: int
    titulo: str
    puntaje: float   # similitud con la pregunta (0 a 1)


class ChatSalida(BaseModel):
    conversacion_id: int
    respuesta: str
    fuentes: list[Fuente]
    suficiente_info: bool        # False si la base de datos no tenía información suficiente
    tokens_consulta: int         # tokens gastados en esta consulta
    tokens_restantes: int        # tokens que le quedan al usuario

    

# ---------- Consumo de tokens ----------
class ConsumoServicio(BaseModel):
    servicio_id: int
    codigo: str
    servicio: str
    consultas: int
    tokens_entrada: int
    tokens_salida: int
    tokens_total: int


class ConsumoDia(BaseModel):
    fecha: date
    consultas: int
    tokens_entrada: int
    tokens_salida: int
    tokens_total: int


class ConsumoDetalle(BaseModel):
    id: int
    fecha_hora: datetime      # hora de Guatemala
    usuario_id: int
    usuario: str
    servicio_id: int
    servicio: str
    conversacion_id: Optional[int] = None
    tokens_entrada: int
    tokens_salida: int
    tokens_total: int


class ResumenConsumo(BaseModel):
    limite_tokens: int
    tokens_usados: int
    tokens_restantes: int
    consultas: int
    por_servicio: list[ConsumoServicio]


# ---------- Historial ----------
class ConversacionResumen(BaseModel):
    id: int
    titulo: str
    servicio_id: int
    servicio: str
    usuario_id: int
    usuario: str
    creada_en: datetime
    mensajes: int
    tokens_total: int


class MensajeSalida(BaseModel):
    id: int
    rol: str
    contenido: str
    fuentes: Optional[list[Fuente]] = None
    creado_en: datetime


class ConversacionDetalle(ConversacionResumen):
    lista_mensajes: list[MensajeSalida]