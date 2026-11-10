"""Embeddings con la API de Google (Gemini). Antes se calculaban dentro del servidor con fastembed,
pero el modelo no cabe en los 512 MB del plan gratuito de Render. Ahora el servidor solo envía el
texto y recibe el vector: casi no usa memoria.

La interfaz (embed, embed_uno, a_literal) es la misma de antes, así que el resto del código no cambia."""
import logging
import math
import time

import httpx
from fastapi import HTTPException

from . import config

MODELO = "gemini-embedding-001"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:batchEmbedContents"
DIMENSIONES = 384        # debe coincidir con vector(384) de la tabla documentos_rag
LOTE = 20                # textos por petición (el plan gratuito limita tokens por minuto)
REINTENTOS = 4


def _normalizar(vector: list[float]) -> list[float]:
    """Con menos de 3072 dimensiones, Google pide normalizar el vector (longitud 1)."""
    norma = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norma for x in vector]


def _enviar(textos: list[str], tipo_tarea: str) -> list[list[float]]:
    """Una petición con varios textos. Reintenta si se supera el límite por minuto (429)."""
    if not config.GOOGLE_API_KEY:
        raise HTTPException(503, "Falta GOOGLE_API_KEY en las variables de entorno")
    cuerpo = {"requests": [
        {
            "model": f"models/{MODELO}",
            "content": {"parts": [{"text": t}]},
            "taskType": tipo_tarea,                 # RETRIEVAL_QUERY o RETRIEVAL_DOCUMENT
            "outputDimensionality": DIMENSIONES,
        }
        for t in textos
    ]}
    cabeceras = {"x-goog-api-key": config.GOOGLE_API_KEY}

    for intento in range(1, REINTENTOS + 1):
        try:
            resp = httpx.post(URL, json=cuerpo, headers=cabeceras, timeout=30.0)
        except httpx.HTTPError:
            logging.exception("No se pudo contactar con la API de embeddings")
            raise HTTPException(502, "No se pudo contactar con el servicio de embeddings.")
        if resp.status_code == 429 and intento < REINTENTOS:
            time.sleep(15 * intento)                # espera y reintenta
            continue
        if resp.status_code == 429:
            raise HTTPException(503, "El servicio de embeddings está saturado. Intenta en un minuto.")
        if resp.status_code != 200:
            logging.error("Embeddings respondió %s: %s", resp.status_code, resp.text[:300])
            raise HTTPException(502, "El servicio de embeddings devolvió un error.")
        return [_normalizar(e["values"]) for e in resp.json()["embeddings"]]


def embed(textos: list[str]) -> list[list[float]]:
    """Vectores de DOCUMENTOS (se usa al indexar). Devuelve un vector de 384 números por texto."""
    vectores = []
    for i in range(0, len(textos), LOTE):
        vectores += _enviar(textos[i:i + LOTE], "RETRIEVAL_DOCUMENT")
    return vectores


def embed_uno(texto: str) -> list[float]:
    """Vector de una PREGUNTA (se usa al buscar). Google optimiza distinto consultas y documentos."""
    return _enviar([texto], "RETRIEVAL_QUERY")[0]


def a_literal(vector: list[float]) -> str:
    """Formato de texto que entiende pgvector: '[0.1,0.2,...]'"""
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"
