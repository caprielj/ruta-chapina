"""Control y registro del consumo de tokens (bloqueo por límite)."""
import pytest
from fastapi import HTTPException

from app import consumo
from tests.conftest import usuario_demo


def test_tokens_usados_devuelve_la_suma(bd):
    bd.cuando("SUM(tokens_total)", {"total": 1234})
    assert consumo.tokens_usados(1) == 1234


def test_verificar_limite_deja_pasar_si_queda_saldo(bd):
    bd.cuando("SUM(tokens_total)", {"total": 500})
    assert consumo.verificar_limite(usuario_demo(limite_tokens=1000)) == 500


def test_verificar_limite_bloquea_al_alcanzarlo(bd):
    bd.cuando("SUM(tokens_total)", {"total": 1000})   # justo en el límite
    with pytest.raises(HTTPException) as e:
        consumo.verificar_limite(usuario_demo(limite_tokens=1000))
    assert e.value.status_code == 429


def test_verificar_limite_bloquea_si_lo_supero(bd):
    bd.cuando("SUM(tokens_total)", {"total": 5000})
    with pytest.raises(HTTPException) as e:
        consumo.verificar_limite(usuario_demo(limite_tokens=1000))
    assert e.value.status_code == 429


def test_limite_cero_bloquea_el_uso_de_ia(bd):
    """Una cuenta con límite 0 (como la de Power BI) no puede consumir IA."""
    bd.cuando("SUM(tokens_total)", {"total": 0})
    with pytest.raises(HTTPException) as e:
        consumo.verificar_limite(usuario_demo(limite_tokens=0))
    assert e.value.status_code == 429


def test_registrar_inserta_una_fila_con_los_tokens(bd):
    bd.cuando("INSERT INTO consumo_tokens", 1)
    consumo.registrar(usuario_id=3, servicio_id=2, conversacion_id=9, tokens_entrada=120, tokens_salida=30)
    (_, _, params), = bd.llamadas_con("INSERT INTO consumo_tokens")
    assert params == (3, 2, 9, 120, 30)


def test_registrar_acepta_cero_tokens(bd):
    """Una consulta sin llamar al modelo igual cuenta como consulta realizada."""
    bd.cuando("INSERT INTO consumo_tokens", 1)
    consumo.registrar(1, 1, None, 0, 0)
    assert bd.llamadas_con("INSERT INTO consumo_tokens")[0][2] == (1, 1, None, 0, 0)
