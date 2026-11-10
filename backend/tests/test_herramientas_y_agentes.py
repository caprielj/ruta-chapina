"""Herramientas del agente (cálculos exactos) y bucle del agente de varios pasos."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import agentes, herramientas
from tests.conftest import usuario_demo

ANTIGUA = {"id": 1, "nombre": "Antigua Guatemala", "departamento": "Sacatepéquez",
           "categoria": "cultural", "costo_diario_gtq": 300, "mejor_epoca": "noviembre-abril",
           "latitud": 14.5586, "longitud": -90.7295}


# ---------------------------------------------------------------- herramientas
def test_haversine_misma_posicion_es_cero():
    assert herramientas._haversine(14.6, -90.5, 14.6, -90.5) == pytest.approx(0)


def test_haversine_ciudad_de_guatemala_a_antigua_ronda_25_km():
    km = herramientas._haversine(14.6349, -90.5069, 14.5586, -90.7295)
    assert 22 < km < 28


def test_calcular_presupuesto_hace_la_aritmetica_en_codigo(bd):
    bd.cuando("FROM destinos WHERE id = ANY", [ANTIGUA])
    bd.cuando("FROM actividades WHERE id = ANY", [
        {"nombre": "Volcán Pacaya", "costo_gtq": 50}, {"nombre": "Tour", "costo_gtq": 100}])
    r = herramientas.calcular_presupuesto(
        personas=2, tramos=[{"destino_id": 1, "dias": 3, "actividad_ids": [10, 11]}])
    # base: 300 x 3 días x 2 personas = 1800; actividades: (50+100) x 2 = 300
    assert r["tramos"][0]["alojamiento_comida_gtq"] == 1800
    assert r["tramos"][0]["actividades_gtq"] == 300
    assert r["total_gtq"] == 2100
    assert r["por_persona_gtq"] == 1050


def test_calcular_presupuesto_minimo_una_persona_y_un_dia(bd):
    bd.cuando("FROM destinos WHERE id = ANY", [ANTIGUA])
    r = herramientas.calcular_presupuesto(personas=0, tramos=[{"destino_id": 1, "dias": 0}])
    assert r["personas"] == 1
    assert r["total_gtq"] == 300


def test_calcular_presupuesto_ignora_destinos_inexistentes(bd):
    bd.cuando("FROM destinos WHERE id = ANY", [])
    r = herramientas.calcular_presupuesto(personas=2, tramos=[{"destino_id": 999, "dias": 2}])
    assert r["total_gtq"] == 0 and r["tramos"] == []


def test_ejecutar_herramienta_inexistente_devuelve_error_sin_lanzar():
    assert "error" in herramientas.ejecutar("hackear_nasa", {})


def test_ejecutar_con_argumentos_invalidos_devuelve_error_sin_lanzar():
    assert "error" in herramientas.ejecutar("calcular_presupuesto", {"argumento_raro": 1})


# ---------------------------------------------------------------- bucle del agente
def llamada(nombre, argumentos="{}", id_="c1"):
    return SimpleNamespace(id=id_, function=SimpleNamespace(name=nombre, arguments=argumentos))


def mensaje_con_herramienta(nombre, argumentos="{}"):
    return SimpleNamespace(content="", tool_calls=[llamada(nombre, argumentos)])


def mensaje_final(texto):
    return SimpleNamespace(content=texto, tool_calls=None)


def preparar_agente(bd, usados=0, activo=True):
    bd.cuando("FROM servicios_ia WHERE codigo", {"id": 2, "activo": activo})
    bd.cuando("SUM(tokens_total)", {"total": usados})
    bd.cuando("INSERT INTO resultados_agentes", {"id": 99})
    bd.cuando("INSERT INTO consumo_tokens", 1)


def test_agente_usa_herramientas_y_luego_responde(bd, monkeypatch):
    preparar_agente(bd)
    turnos = iter([
        (mensaje_con_herramienta("buscar_destinos", '{"consulta": "volcanes"}'), 100, 20),
        (mensaje_final("Plan de 3 días en Antigua."), 150, 60),
    ])
    monkeypatch.setattr(agentes.llm, "completar_agente", lambda m, e=None: next(turnos))
    monkeypatch.setattr(agentes.herramientas, "ejecutar", lambda n, a: {
        "destinos": [{"id": 1, "nombre": "Antigua Guatemala", "departamento": "Sacatepéquez",
                      "lat": 14.55, "lon": -90.73}]})

    r = agentes.correr_agente("planificador_ruta", usuario_demo(), "Viaje de 3 días con volcanes")

    assert r["respuesta"] == "Plan de 3 días en Antigua."
    assert [p["herramienta"] for p in r["pasos"]] == ["buscar_destinos"]
    assert r["destinos"][0]["nombre"] == "Antigua Guatemala"     # alimenta el mapa
    assert r["tokens_consulta"] == (100 + 20) + (150 + 60)       # suma de TODAS las vueltas
    assert r["resultado_id"] == 99
    # el consumo se registra una sola vez, con la suma
    assert bd.llamadas_con("INSERT INTO consumo_tokens")[0][2] == (1, 2, None, 250, 80)


def test_agente_sin_herramientas_responde_directo(bd, monkeypatch):
    preparar_agente(bd)
    monkeypatch.setattr(agentes.llm, "completar_agente", lambda m, e=None: (mensaje_final("Listo."), 10, 5))
    r = agentes.correr_agente("planificador_ruta", usuario_demo(), "Algo sencillo de prueba")
    assert r["pasos"] == [] and r["respuesta"] == "Listo."


def test_agente_corta_en_el_maximo_de_rondas_y_pide_la_respuesta_final(bd, monkeypatch):
    preparar_agente(bd)
    llamadas = []

    def _llm(mensajes, esquemas=None):
        llamadas.append(esquemas)
        if esquemas is None:    # la vuelta final se pide SIN herramientas
            return mensaje_final("Respuesta forzada."), 5, 5
        return mensaje_con_herramienta("consultar_clima", '{"destino_ids": [1]}'), 5, 5

    monkeypatch.setattr(agentes.llm, "completar_agente", _llm)
    monkeypatch.setattr(agentes.herramientas, "ejecutar", lambda n, a: {"clima": []})

    r = agentes.correr_agente("planificador_ruta", usuario_demo(), "Plan que nunca termina")

    assert len(llamadas) == agentes.MAX_RONDAS + 1
    assert r["respuesta"] == "Respuesta forzada."


def test_agente_bloqueado_por_limite_no_llama_al_modelo(bd, monkeypatch):
    preparar_agente(bd, usados=20000)

    def _no_debe_llamarse(*a, **k):
        raise AssertionError("Con el límite alcanzado no debe llamar al modelo")
    monkeypatch.setattr(agentes.llm, "completar_agente", _no_debe_llamarse)

    with pytest.raises(HTTPException) as e:
        agentes.correr_agente("planificador_ruta", usuario_demo(limite_tokens=20000), "Quiero un plan")
    assert e.value.status_code == 429


def test_agente_desactivado_da_403(bd):
    preparar_agente(bd, activo=False)
    with pytest.raises(HTTPException) as e:
        agentes.correr_agente("planificador_ruta", usuario_demo(), "Quiero un plan")
    assert e.value.status_code == 403
