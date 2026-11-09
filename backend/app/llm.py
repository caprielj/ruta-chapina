import logging

from fastapi import HTTPException
from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

from . import config

_cliente = None


def _obtener_cliente() -> Groq:
    global _cliente
    if _cliente is None:
        if not config.GROQ_API_KEY:
            raise HTTPException(503, "Falta GROQ_API_KEY en el .env")
        _cliente = Groq(api_key=config.GROQ_API_KEY, timeout=30.0)
    return _cliente


def completar(mensajes: list[dict], temperatura: float = 0.3, max_tokens: int = 1500):
    """Envía la conversación a Groq y devuelve (texto, tokens_entrada, tokens_salida)."""
    parametros = {}
    # Los modelos gpt-oss razonan antes de responder. Pedimos poco razonamiento para que
    # gasten menos tokens y respondan más rápido (extra_body envía el campo tal cual a la API).
    if config.GROQ_MODEL.startswith("openai/gpt-oss"):
        parametros["extra_body"] = {"reasoning_effort": "low"}
    try:
        resp = _obtener_cliente().chat.completions.create(
            model=config.GROQ_MODEL,
            messages=mensajes,
            temperature=temperatura,   # bajo = respuestas más fieles al contexto
            max_tokens=max_tokens,     # en modelos de razonamiento incluye el "pensamiento"
            **parametros,
        )
    except RateLimitError:
        raise HTTPException(503, "El proveedor de IA está saturado. Intenta de nuevo en unos segundos.")
    except (APIConnectionError, APIStatusError):
        logging.exception("Error llamando a Groq")   # el detalle queda en la terminal
        raise HTTPException(502, "No se pudo obtener respuesta del proveedor de IA.")
    texto = (resp.choices[0].message.content or "").strip()
    if not texto:
        # Pasa si el modelo gastó todo el margen razonando
        raise HTTPException(502, "El modelo devolvió una respuesta vacía. Intenta de nuevo.")
    uso = resp.usage
    return texto, uso.prompt_tokens, uso.completion_tokens