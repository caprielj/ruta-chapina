"""Contraseñas, JWT y roles."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app import config, seguridad
from tests.conftest import usuario_demo


def test_hash_no_guarda_la_contrasena_y_se_verifica():
    h = seguridad.hashear("Clave-segura-1")
    assert h != "Clave-segura-1"
    assert seguridad.verificar("Clave-segura-1", h) is True
    assert seguridad.verificar("otra-clave", h) is False


def test_verificar_con_hash_invalido_devuelve_false():
    assert seguridad.verificar("lo-que-sea", "esto-no-es-un-hash") is False


def test_token_contiene_id_y_rol():
    datos = jwt.decode(seguridad.crear_token(usuario_demo(id=7, rol="admin")),
                       config.JWT_SECRET, algorithms=[config.JWT_ALGORITMO])
    assert datos["sub"] == "7"
    assert datos["rol"] == "admin"


def test_usuario_actual_rechaza_token_invalido():
    with pytest.raises(HTTPException) as e:
        seguridad.usuario_actual("token-inventado")
    assert e.value.status_code == 401


def test_usuario_actual_rechaza_token_expirado():
    vencido = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        config.JWT_SECRET, algorithm=config.JWT_ALGORITMO)
    with pytest.raises(HTTPException) as e:
        seguridad.usuario_actual(vencido)
    assert e.value.status_code == 401


def test_usuario_actual_rechaza_token_firmado_con_otra_clave():
    falso = jwt.encode({"sub": "1"}, "otra-clave-distinta-de-32-bytes-o-mas!!", algorithm="HS256")
    with pytest.raises(HTTPException) as e:
        seguridad.usuario_actual(falso)
    assert e.value.status_code == 401


def test_usuario_desactivado_pierde_el_acceso(bd):
    bd.cuando("FROM usuarios WHERE id", usuario_demo(activo=False))
    with pytest.raises(HTTPException) as e:
        seguridad.usuario_actual(seguridad.crear_token(usuario_demo()))
    assert e.value.status_code == 401


def test_usuario_activo_pasa(bd):
    bd.cuando("FROM usuarios WHERE id", usuario_demo())
    assert seguridad.usuario_actual(seguridad.crear_token(usuario_demo()))["id"] == 1


def test_solo_admin_bloquea_a_usuarios_normales():
    with pytest.raises(HTTPException) as e:
        seguridad.solo_admin(usuario_demo(rol="usuario"))
    assert e.value.status_code == 403
    assert seguridad.solo_admin(usuario_demo(rol="admin"))["rol"] == "admin"
