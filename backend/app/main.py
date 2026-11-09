import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, db
from .routers import auth, entidades, servicios, usuarios

app = FastAPI(
    title="Ruta Chapina API",
    version="0.2.0",
    description="API de turismo y gastronomía de Guatemala con servicios de IA.",
)

# CORS: permite que el frontend (otro dominio/puerto) llame a esta API desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registramos cada grupo de endpoints
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(servicios.router)
app.include_router(entidades.router_destinos)
app.include_router(entidades.router_actividades)
app.include_router(entidades.router_platillos)


@app.get("/salud", tags=["Salud"])
def salud():
    """Comprueba que el servidor está despierto."""
    return {"estado": "ok", "proyecto": "Ruta Chapina"}


@app.get("/salud/db", tags=["Salud"])
def salud_db():
    """Comprueba que la API puede hablar con la base de datos."""
    try:
        db.uno("SELECT 1 AS ok")
        return {"base_de_datos": "ok"}
    except Exception:
        logging.exception("Fallo al conectar con la base de datos")  # el detalle sale en la terminal
        raise HTTPException(503, "No se pudo conectar a la base de datos")