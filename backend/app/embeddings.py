from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def _modelo():
    """Carga el modelo una sola vez, la primera vez que se necesita.
    La primera ejecución lo descarga (~220 MB) y queda guardado en caché."""
    from fastembed import TextEmbedding   # import tardío: no gasta memoria hasta que se usa
    return TextEmbedding(model_name=config.EMBEDDING_MODEL)


def embed(textos: list[str]) -> list[list[float]]:
    """Convierte una lista de textos en vectores (un vector de 384 números por texto)."""
    return [vector.tolist() for vector in _modelo().embed(textos)]


def embed_uno(texto: str) -> list[float]:
    return embed([texto])[0]


def a_literal(vector: list[float]) -> str:
    """Formato de texto que entiende pgvector: '[0.1,0.2,...]'"""
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"