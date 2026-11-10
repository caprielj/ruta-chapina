"""Preparación común de las pruebas.

Objetivo: que NINGUNA prueba toque la base de datos real ni gaste tokens de Groq.
 - Se fijan variables de entorno falsas ANTES de importar la app (config.py las exige).
 - La base de datos se reemplaza por una "BD falsa" que responde según reglas.
"""
import os

# Variables falsas: tienen prioridad sobre el .env real (load_dotenv no pisa lo ya definido)
os.environ["DATABASE_URL"] = "postgresql://prueba:prueba@localhost:5432/prueba"
os.environ["JWT_SECRET"] = "secreto-solo-para-pruebas-con-32-caracteres-o-mas"
os.environ["GROQ_API_KEY"] = "clave-falsa"

import pytest
from fastapi.testclient import TestClient

from app import db, seguridad
from app.main import app


class BDFalsa:
    """Sustituye a db.uno / db.todos / db.ejecutar.

    Se le dice qué responder con bd.cuando("fragmento de SQL", respuesta).
    Si la app lanza una consulta que nadie previó, la prueba falla: así detectamos
    consultas inesperadas en lugar de ocultarlas.
    """

    def __init__(self):
        self.reglas = []     # lista de (fragmento_sql, respuesta)
        self.llamadas = []   # historial de (tipo, sql, params) para poder verificarlo

    def cuando(self, fragmento, respuesta):
        # la respuesta puede ser un valor fijo o una función(params) -> valor
        self.reglas.append((" ".join(fragmento.split()), respuesta))

    def _resolver(self, tipo, sql, params):
        sql = " ".join(sql.split())
        self.llamadas.append((tipo, sql, params))
        for fragmento, respuesta in self.reglas:
            if fragmento in sql:
                return respuesta(params) if callable(respuesta) else respuesta
        raise AssertionError(f"Consulta SQL inesperada ({tipo}): {sql[:120]}")

    def llamadas_con(self, fragmento):
        """Llamadas cuyo SQL contiene el fragmento (para verificar INSERT, etc.)."""
        return [c for c in self.llamadas if " ".join(fragmento.split()) in c[1]]


@pytest.fixture
def bd(monkeypatch):
    falsa = BDFalsa()
    monkeypatch.setattr(db, "uno", lambda sql, params=None: falsa._resolver("uno", sql, params))
    monkeypatch.setattr(db, "todos", lambda sql, params=None: falsa._resolver("todos", sql, params))
    monkeypatch.setattr(db, "ejecutar", lambda sql, params=None: falsa._resolver("ejecutar", sql, params))
    return falsa


@pytest.fixture(autouse=True)
def sin_bd_real(monkeypatch):
    """Red de seguridad: si algo intentara abrir una conexión real, la prueba falla."""
    def _prohibido():
        raise AssertionError("Una prueba intentó conectarse a la base de datos real")
    monkeypatch.setattr(db, "_obtener_pool", _prohibido)


@pytest.fixture
def cliente():
    return TestClient(app)


def usuario_demo(**cambios):
    base = {"id": 1, "nombre": "Ana", "email": "ana@test.com", "rol": "usuario",
            "activo": True, "limite_tokens": 20000}
    base.update(cambios)
    return base


@pytest.fixture
def con_sesion(bd):
    """Devuelve una función que 'inicia sesión': crea un token y hace que usuario_actual
    encuentre al usuario en la BD falsa. Se usa como: cabeceras = con_sesion(rol='admin')."""
    def _iniciar(**cambios):
        usuario = usuario_demo(**cambios)
        bd.cuando("FROM usuarios WHERE id", usuario)
        token = seguridad.crear_token(usuario)
        return {"Authorization": f"Bearer {token}"}
    return _iniciar
