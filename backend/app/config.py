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

# ---------- IA ----------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Si Groq retira este modelo, cámbialo en el .env sin tocar el código
# (lista vigente en https://console.groq.com/docs/models)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Modelo de embeddings: multilingüe (entiende español), produce vectores de 384 dimensiones
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))          # cuántos fragmentos se recuperan
RAG_UMBRAL = float(os.getenv("RAG_UMBRAL", "0.30"))   # similitud mínima (0 a 1) para usar un fragmento
MEMORIA_MENSAJES = int(os.getenv("MEMORIA_MENSAJES", "6"))  # mensajes previos que recuerda el chat