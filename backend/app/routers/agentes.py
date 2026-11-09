from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import agentes as motor, db
from ..schemas import (AgenteEntrada, AgenteSalida, AjusteEntrada,
                       ResultadoAgenteDetalle, ResultadoAgenteResumen)
from ..seguridad import usuario_actual

router = APIRouter(prefix="/agentes", tags=["Agentes de IA"])

BASE = """
    SELECT r.id, r.servicio_id, s.nombre AS servicio, r.usuario_id, u.nombre AS usuario,
           r.solicitud, r.creado_en, r.pasos, r.resultado
    FROM resultados_agentes r
    JOIN servicios_ia s ON s.id = r.servicio_id
    JOIN usuarios u ON u.id = r.usuario_id
"""


@router.post("/planificador", response_model=AgenteSalida)
def planificador(datos: AgenteEntrada, usuario: dict = Depends(usuario_actual)):
    """Arma un itinerario: busca destinos, consulta clima y distancias, y calcula el presupuesto."""
    return motor.correr_agente("planificador_ruta", usuario, datos.solicitud)


@router.post("/ajuste", response_model=AgenteSalida)
def ajuste(datos: AjusteEntrada, usuario: dict = Depends(usuario_actual)):
    """Reajusta un plan ante un cambio de clima o de presupuesto, buscando alternativas."""
    return motor.correr_agente("ajuste_plan", usuario, datos.solicitud, datos.plan_previo_id)


@router.get("/resultados", response_model=list[ResultadoAgenteResumen])
def listar(
    servicio_id: Optional[int] = None,
    usuario_id: Optional[int] = Query(None, description="Solo el administrador puede usarlo"),
    limite: int = Query(50, ge=1, le=500),
    usuario: dict = Depends(usuario_actual),
):
    """Resultados anteriores. El usuario ve los suyos; el admin ve los de todos."""
    if usuario["rol"] != "admin":
        if usuario_id not in (None, usuario["id"]):
            raise HTTPException(403, "Solo puedes consultar tus propios resultados")
        usuario_id = usuario["id"]
    cond, params = [], []
    if usuario_id is not None:
        cond.append("r.usuario_id = %s"); params.append(usuario_id)
    if servicio_id is not None:
        cond.append("r.servicio_id = %s"); params.append(servicio_id)
    donde = " WHERE " + " AND ".join(cond) if cond else ""
    return db.todos(BASE + donde + " ORDER BY r.id DESC LIMIT %s", params + [limite])


@router.get("/resultados/{resultado_id}", response_model=ResultadoAgenteDetalle)
def ver(resultado_id: int, usuario: dict = Depends(usuario_actual)):
    fila = db.uno(BASE + " WHERE r.id = %s", (resultado_id,))
    if not fila or (usuario["rol"] != "admin" and fila["usuario_id"] != usuario["id"]):
        raise HTTPException(404, "Resultado no encontrado")   # 404: no revelamos que existe
    return fila