import os
from pathlib import Path
from dotenv import load_dotenv

# El .env está en la raíz del proyecto (dos niveles arriba de este archivo: app -> backend -> raíz)
RAIZ = Path(__file__).resolve().parents[2]
# En producción (Render) las variables vienen del servidor; load_dotenv no pisa las que ya existen
load_dotenv(RAIZ / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITMO = "HS256"                          # algoritmo con el que se firma el token
JWT_HORAS = int(os.getenv("JWT_HORAS", "12"))    # cuánto dura una sesión

# Orígenes permitidos para el frontend (CORS), separados por coma
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

# Si falta algo esencial, fallamos de inmediato con un mensaje claro
if not DATABASE_URL or not JWT_SECRET:
    raise RuntimeError("Faltan DATABASE_URL o JWT_SECRET en el archivo .env")