"""Chatbot RAG: recuperación, respuesta sin información, citas, historial (memoria) y tokens."""
import pytest
from fastapi import HTTPException

from app import chatbot, config
from tests.conftest import usuario_demo

FRAGMENTO = {"fuente_tabla": "destinos", "fuente_id": 1, "titulo": "Antigua Guatemala",
             "contenido": "Ciudad colonial rodeada de volcanes.", "similitud": 0.82}


def preparar(bd, usados=0, servicio_activo=True):
    """Reglas de BD que el chatbot necesita en un flujo normal."""
    bd.cuando("FROM servicios_ia WHERE codigo = 'chatbot_rag'", {"id": 1, "activo": servicio_activo})
    bd.cuando("SUM(tokens_total)", {"total": usados})
    bd.cuando("INSERT INTO conversaciones", {"id": 55})
    bd.cuando("INSERT INTO mensajes", 1)
    bd.cuando("INSERT INTO consumo_tokens", 1)


# ---------------------------------------------------------------- recuperación
def test_recuperar_descarta_fragmentos_bajo_el_umbral(bd, monkeypatch):
    monkeypatch.setattr(chatbot.embeddings, "embed_uno", lambda texto: [0.1] * 384)
    bd.cuando("FROM documentos_rag", [
        {**FRAGMENTO, "similitud": config.RAG_UMBRAL + 0.2},
        {**FRAGMENTO, "fuente_id": 2, "similitud": config.RAG_UMBRAL - 0.1},
    ])
    resultado = chatbot.recuperar("volcanes")
    assert [f["fuente_id"] for f in resultado] == [1]


# ---------------------------------------------------------------- sin información
def test_sin_contexto_no_llama_al_modelo_ni_gasta_tokens(bd, monkeypatch):
    preparar(bd)
    monkeypatch.setattr(chatbot, "recuperar", lambda consulta: [])

    def _no_debe_llamarse(*a, **k):
        raise AssertionError("No debía llamar al modelo sin contexto")
    monkeypatch.setattr(chatbot.llm, "completar", _no_debe_llamarse)

    r = chatbot.conversar(usuario_demo(), "¿Cuál es la capital de Francia?", None)
    assert chatbot.FRASE_SIN_INFO in r["respuesta"]
    assert r["suficiente_info"] is False
    assert r["fuentes"] == []
    assert r["tokens_consulta"] == 0
    # aun así queda registrada como consulta (0 tokens)
    assert bd.llamadas_con("INSERT INTO consumo_tokens")[0][2] == (1, 1, 55, 0, 0)


def test_si_el_modelo_dice_no_tengo_informacion_no_se_citan_fuentes(bd, monkeypatch):
    preparar(bd)
    monkeypatch.setattr(chatbot, "recuperar", lambda consulta: [FRAGMENTO])
    monkeypatch.setattr(chatbot.llm, "completar",
                        lambda m, **k: ("No tengo información suficiente sobre eso.", 80, 20))
    r = chatbot.conversar(usuario_demo(), "¿Hay playa en Antigua?", None)
    assert r["suficiente_info"] is False
    assert r["fuentes"] == []


# ---------------------------------------------------------------- respuesta con fuentes
def test_respuesta_cita_fuentes_y_registra_tokens(bd, monkeypatch):
    preparar(bd, usados=1000)
    monkeypatch.setattr(chatbot, "recuperar", lambda consulta: [FRAGMENTO])
    monkeypatch.setattr(chatbot.llm, "completar", lambda m, **k: ("Visita Antigua [1].", 100, 50))

    r = chatbot.conversar(usuario_demo(limite_tokens=20000), "¿Qué hago en Antigua?", None)

    assert r["conversacion_id"] == 55
    assert r["suficiente_info"] is True
    assert r["fuentes"] == [{"tabla": "destinos", "id": 1, "titulo": "Antigua Guatemala", "puntaje": 0.82}]
    assert r["tokens_consulta"] == 150
    assert r["tokens_restantes"] == 20000 - 1000 - 150
    # consumo guardado con entrada y salida por separado
    assert bd.llamadas_con("INSERT INTO consumo_tokens")[0][2] == (1, 1, 55, 100, 50)


def test_guarda_el_historial_pregunta_y_respuesta(bd, monkeypatch):
    preparar(bd)
    monkeypatch.setattr(chatbot, "recuperar", lambda consulta: [FRAGMENTO])
    monkeypatch.setattr(chatbot.llm, "completar", lambda m, **k: ("Respuesta.", 10, 5))

    chatbot.conversar(usuario_demo(), "Hola Antigua", None)

    mensajes = bd.llamadas_con("INSERT INTO mensajes")
    assert len(mensajes) == 2
    assert mensajes[0][1].count("'user'") == 1 and mensajes[0][2] == (55, "Hola Antigua")
    assert mensajes[1][1].count("'assistant'") == 1 and mensajes[1][2][1] == "Respuesta."


def test_conversacion_nueva_usa_el_inicio_de_la_pregunta_como_titulo(bd, monkeypatch):
    preparar(bd)
    monkeypatch.setattr(chatbot, "recuperar", lambda consulta: [FRAGMENTO])
    monkeypatch.setattr(chatbot.llm, "completar", lambda m, **k: ("Ok.", 1, 1))
    pregunta = "x" * 200
    chatbot.conversar(usuario_demo(), pregunta, None)
    assert bd.llamadas_con("INSERT INTO conversaciones")[0][2][2] == "x" * 60


# ---------------------------------------------------------------- memoria
def test_memoria_envia_el_historial_al_modelo_y_une_la_pregunta_previa(bd, monkeypatch):
    preparar(bd)
    bd.cuando("FROM conversaciones WHERE id", {"id": 7})
    bd.cuando("FROM mensajes WHERE conversacion_id", [
        {"rol": "user", "contenido": "¿Qué hay en Antigua?"},
        {"rol": "assistant", "contenido": "Hay iglesias y volcanes."},
    ])
    consultas, enviados = [], []

    def _recuperar(consulta):
        consultas.append(consulta)
        return [FRAGMENTO]

    def _completar(mensajes, **k):
        enviados.extend(mensajes)
        return "Cuesta unos Q300 diarios [1].", 90, 30

    monkeypatch.setattr(chatbot, "recuperar", _recuperar)
    monkeypatch.setattr(chatbot.llm, "completar", _completar)

    chatbot.conversar(usuario_demo(), "¿Y cuánto cuesta?", 7)

    # el seguimiento se busca junto a la pregunta anterior, para no perder el tema
    assert "Antigua" in consultas[0] and "cuánto cuesta" in consultas[0]
    # el modelo recibe: sistema + historial previo + pregunta actual con contexto
    roles = [m["role"] for m in enviados]
    assert roles == ["system", "user", "assistant", "user"]
    assert "Hay iglesias y volcanes." in enviados[2]["content"]
    assert "¿Y cuánto cuesta?" in enviados[3]["content"]
    # sigue la misma conversación (no crea otra)
    assert not bd.llamadas_con("INSERT INTO conversaciones")


def test_conversacion_de_otro_usuario_da_404(bd):
    preparar(bd)
    bd.cuando("FROM conversaciones WHERE id", None)   # no es suya o no existe
    with pytest.raises(HTTPException) as e:
        chatbot.conversar(usuario_demo(), "Hola", 999)
    assert e.value.status_code == 404


# ---------------------------------------------------------------- bloqueo y servicio
def test_limite_alcanzado_bloquea_antes_de_llamar_al_modelo(bd, monkeypatch):
    preparar(bd, usados=20000)

    def _no_debe_llamarse(*a, **k):
        raise AssertionError("Con el límite alcanzado no debe llamar al modelo")
    monkeypatch.setattr(chatbot.llm, "completar", _no_debe_llamarse)
    monkeypatch.setattr(chatbot, "recuperar", _no_debe_llamarse)

    with pytest.raises(HTTPException) as e:
        chatbot.conversar(usuario_demo(limite_tokens=20000), "Hola", None)
    assert e.value.status_code == 429
    assert not bd.llamadas_con("INSERT INTO")     # no se guardó nada


def test_servicio_desactivado_da_403(bd):
    preparar(bd, servicio_activo=False)
    with pytest.raises(HTTPException) as e:
        chatbot.conversar(usuario_demo(), "Hola", None)
    assert e.value.status_code == 403
