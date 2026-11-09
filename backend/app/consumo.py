from fastapi import HTTPException

from . import db


def tokens_usados(usuario_id: int) -> int:
    """Total de tokens que lleva consumidos un usuario."""
    fila = db.uno(
        "SELECT COALESCE(SUM(tokens_total), 0)::int AS total FROM consumo_tokens WHERE usuario_id = %s",
        (usuario_id,),
    )
    return fila["total"]


def verificar_limite(usuario: dict) -> int:
    """Se llama ANTES de ejecutar un servicio. Bloquea (429) si ya alcanzó su límite.
    Devuelve los tokens usados hasta ahora."""
    usados = tokens_usados(usuario["id"])
    if usados >= usuario["limite_tokens"]:
        raise HTTPException(
            429,
            f"Alcanzaste tu límite de {usuario['limite_tokens']} tokens. "
            "Pide al administrador que lo amplíe.",
        )
    return usados


def registrar(usuario_id: int, servicio_id: int, conversacion_id, tokens_entrada: int, tokens_salida: int):
    """Guarda una fila de consumo (también con 0 tokens, para que cuente como consulta realizada)."""
    db.ejecutar(
        """INSERT INTO consumo_tokens
           (usuario_id, servicio_id, conversacion_id, tokens_entrada, tokens_salida)
           VALUES (%s, %s, %s, %s, %s)""",
        (usuario_id, servicio_id, conversacion_id, tokens_entrada, tokens_salida),
    )