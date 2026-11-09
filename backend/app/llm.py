import logging
import time

from fastapi import HTTPException
from groq import APIConnectionError, APIStatusError, BadRequestError, Groq, RateLimitError

from . import config

_cliente = None


def _obtener_cliente() -> Groq:
    global _cliente
    if _cliente is None:
        if not config.GROQ_API_KEY:
            raise HTTPException(503, "Falta GROQ_API_KEY en el .env")
        _cliente = Groq(api_key=config.GROQ_API_KEY, timeout=40.0)
    return _cliente


def _extra() -> dict:
    """Los modelos gpt-oss razonan antes de responder. Pedimos poco razonamiento para que
    gasten menos tokens (extra_body envía el campo tal cual a la API)."""
    if config.GROQ_MODEL.startswith("openai/gpt-oss"):
        return {"extra_body": {"reasoning_effort": "low"}}
    return {}


def completar(mensajes: list[dict], temperatura: float = 0.3, max_tokens: int = 1500):
    """Chat simple (lo usa el chatbot RAG). Devuelve (texto, tokens_entrada, tokens_salida)."""
    try:
        resp = _obtener_cliente().chat.completions.create(
            model=config.GROQ_MODEL, messages=mensajes,
            temperature=temperatura, max_tokens=max_tokens, **_extra(),
        )
    except RateLimitError:
        raise HTTPException(503, "El proveedor de IA está saturado. Intenta de nuevo en unos segundos.")
    except (APIConnectionError, APIStatusError):
        logging.exception("Error llamando a Groq")
        raise HTTPException(502, "No se pudo obtener respuesta del proveedor de IA.")
    texto = (resp.choices[0].message.content or "").strip()
    if not texto:
        raise HTTPException(502, "El modelo devolvió una respuesta vacía. Intenta de nuevo.")
    uso = resp.usage
    return texto, uso.prompt_tokens, uso.completion_tokens


def _espera(error) -> float:
    """Segundos que Groq pide esperar tras un 429 (cabecera retry-after)."""
    try:
        return float(error.response.headers.get("retry-after", 10))
    except Exception:
        return 10.0


def completar_agente(mensajes: list[dict], herramientas: list[dict] | None = None, max_tokens: int = 2500):
    """Una vuelta del agente: el modelo responde con texto O pide usar herramientas.
    Devuelve (mensaje, tokens_entrada, tokens_salida). Reintenta si el plan gratuito
    se satura por minuto o si el modelo arma mal una llamada a herramienta."""
    parametros = _extra()
    if herramientas:
        parametros["tools"] = herramientas
        parametros["tool_choice"] = "auto"      # el modelo decide si usa herramientas y cuáles

    for intento in range(4):
        try:
            resp = _obtener_cliente().chat.completions.create(
                model=config.GROQ_MODEL, messages=mensajes,
                temperature=0.2, max_tokens=max_tokens, **parametros,
            )
            break
        except RateLimitError as e:
            espera = _espera(e)
            if intento == 3 or espera > 40:
                raise HTTPException(503, "El proveedor de IA está saturado (límite por minuto). Intenta en un minuto.")
            time.sleep(espera + 1)
        except BadRequestError:
            # Suele ser "tool_use_failed": el modelo armó mal la llamada. Reintentar casi siempre lo arregla
            logging.exception("Llamada a herramienta inválida, reintentando")
            if intento >= 2:
                raise HTTPException(502, "El modelo no pudo completar la solicitud. Intenta de nuevo.")
        except (APIConnectionError, APIStatusError):
            logging.exception("Error llamando a Groq")
            raise HTTPException(502, "No se pudo obtener respuesta del proveedor de IA.")

    uso = resp.usage
    return resp.choices[0].message, uso.prompt_tokens, uso.completion_tokens