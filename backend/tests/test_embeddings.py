"""Cliente de embeddings (Google): formato de la petición, normalización, lotes y reintentos."""
import math

import httpx
import pytest
from fastapi import HTTPException

from app import config, embeddings


class Respuesta:
    def __init__(self, codigo=200, cuerpo=None):
        self.status_code = codigo
        self._cuerpo = cuerpo or {}
        self.text = str(cuerpo)

    def json(self):
        return self._cuerpo


def vectores_falsos(n):
    # vector sin normalizar a propósito, para comprobar que la app lo normaliza
    return {"embeddings": [{"values": [3.0, 4.0] + [0.0] * 382} for _ in range(n)]}


@pytest.fixture(autouse=True)
def con_clave(monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(embeddings.time, "sleep", lambda s: None)   # sin esperas reales


def test_embed_uno_pide_384_dimensiones_y_tarea_de_consulta(monkeypatch):
    enviados = []

    def _post(url, json=None, headers=None, timeout=None):
        enviados.append((url, json, headers))
        return Respuesta(200, vectores_falsos(len(json["requests"])))

    monkeypatch.setattr(embeddings.httpx, "post", _post)
    vector = embeddings.embed_uno("¿Qué hay en Antigua?")

    url, cuerpo, cabeceras = enviados[0]
    assert "gemini-embedding-001:batchEmbedContents" in url
    assert cabeceras["x-goog-api-key"] == "clave-de-prueba"
    peticion = cuerpo["requests"][0]
    assert peticion["outputDimensionality"] == 384
    assert peticion["taskType"] == "RETRIEVAL_QUERY"
    assert peticion["content"]["parts"][0]["text"] == "¿Qué hay en Antigua?"
    assert len(vector) == 384


def test_los_vectores_se_normalizan(monkeypatch):
    monkeypatch.setattr(embeddings.httpx, "post",
                        lambda *a, **k: Respuesta(200, vectores_falsos(1)))
    vector = embeddings.embed_uno("hola")
    assert math.sqrt(sum(x * x for x in vector)) == pytest.approx(1.0)
    assert vector[:2] == pytest.approx([0.6, 0.8])


def test_documentos_se_envian_en_lotes_con_tarea_de_documento(monkeypatch):
    lotes = []

    def _post(url, json=None, headers=None, timeout=None):
        lotes.append(json["requests"])
        return Respuesta(200, vectores_falsos(len(json["requests"])))

    monkeypatch.setattr(embeddings.httpx, "post", _post)
    resultado = embeddings.embed([f"texto {i}" for i in range(45)])

    assert len(resultado) == 45
    assert [len(l) for l in lotes] == [20, 20, 5]
    assert all(r["taskType"] == "RETRIEVAL_DOCUMENT" for l in lotes for r in l)


def test_lista_vacia_no_llama_a_la_api(monkeypatch):
    monkeypatch.setattr(embeddings.httpx, "post",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("No debía llamar")))
    assert embeddings.embed([]) == []


def test_reintenta_cuando_hay_limite_por_minuto(monkeypatch):
    respuestas = iter([Respuesta(429), Respuesta(429), Respuesta(200, vectores_falsos(1))])
    monkeypatch.setattr(embeddings.httpx, "post", lambda *a, **k: next(respuestas))
    assert len(embeddings.embed_uno("hola")) == 384


def test_si_el_limite_persiste_devuelve_503(monkeypatch):
    monkeypatch.setattr(embeddings.httpx, "post", lambda *a, **k: Respuesta(429))
    with pytest.raises(HTTPException) as e:
        embeddings.embed_uno("hola")
    assert e.value.status_code == 503


def test_error_del_proveedor_devuelve_502(monkeypatch):
    monkeypatch.setattr(embeddings.httpx, "post", lambda *a, **k: Respuesta(500, {"error": "x"}))
    with pytest.raises(HTTPException) as e:
        embeddings.embed_uno("hola")
    assert e.value.status_code == 502


def test_fallo_de_red_devuelve_502(monkeypatch):
    def _caida(*a, **k):
        raise httpx.ConnectError("sin red")
    monkeypatch.setattr(embeddings.httpx, "post", _caida)
    with pytest.raises(HTTPException) as e:
        embeddings.embed_uno("hola")
    assert e.value.status_code == 502


def test_sin_clave_devuelve_503(monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "")
    with pytest.raises(HTTPException) as e:
        embeddings.embed_uno("hola")
    assert e.value.status_code == 503


def test_a_literal_tiene_formato_pgvector():
    assert embeddings.a_literal([0.5, 0.25]) == "[0.500000,0.250000]"
