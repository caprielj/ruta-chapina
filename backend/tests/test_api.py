"""Pruebas de extremo a extremo de la API (con BD y modelo simulados):
login, roles, historial, reporte de consumo y bloqueo por límite."""
from datetime import datetime

from app import chatbot, seguridad

FRAGMENTO = {"fuente_tabla": "destinos", "fuente_id": 1, "titulo": "Antigua Guatemala",
             "contenido": "Ciudad colonial.", "similitud": 0.9}


# ---------------------------------------------------------------- salud
def test_salud(cliente):
    r = cliente.get("/salud")
    assert r.status_code == 200 and r.json()["estado"] == "ok"


# ---------------------------------------------------------------- login
def _usuario_bd(**cambios):
    base = {"id": 1, "nombre": "Ana", "email": "ana@test.com", "rol": "usuario", "activo": True,
            "password_hash": seguridad.hashear("Clave-segura-1")}
    base.update(cambios)
    return base


def _login(cliente, email="ana@test.com", password="Clave-segura-1"):
    # el formulario OAuth2 usa el campo "username" para el correo
    return cliente.post("/auth/login", data={"username": email, "password": password})


def test_login_correcto_devuelve_token_y_rol(cliente, bd):
    bd.cuando("FROM usuarios WHERE email", _usuario_bd())
    r = _login(cliente)
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer" and r.json()["rol"] == "usuario"
    assert r.json()["access_token"]


def test_login_con_contrasena_incorrecta(cliente, bd):
    bd.cuando("FROM usuarios WHERE email", _usuario_bd())
    assert _login(cliente, password="incorrecta").status_code == 401


def test_login_con_correo_inexistente_da_el_mismo_error(cliente, bd):
    bd.cuando("FROM usuarios WHERE email", None)
    r = _login(cliente, email="nadie@test.com")
    assert r.status_code == 401 and r.json()["detail"] == "Correo o contraseña incorrectos"


def test_login_de_usuario_desactivado(cliente, bd):
    bd.cuando("FROM usuarios WHERE email", _usuario_bd(activo=False))
    assert _login(cliente).status_code == 401


# ---------------------------------------------------------------- roles
def test_endpoint_protegido_sin_token_da_401(cliente):
    assert cliente.get("/usuarios").status_code == 401
    assert cliente.post("/chat", json={"mensaje": "hola"}).status_code == 401


def test_usuario_normal_no_puede_administrar_usuarios(cliente, con_sesion):
    r = cliente.get("/usuarios", headers=con_sesion(rol="usuario"))
    assert r.status_code == 403


def test_usuario_normal_no_puede_reindexar_el_rag(cliente, con_sesion):
    assert cliente.post("/rag/reindexar", headers=con_sesion(rol="usuario")).status_code == 403


def test_admin_si_puede_listar_usuarios(cliente, bd, con_sesion):
    cabeceras = con_sesion(rol="admin")
    bd.cuando("FROM usuarios u ORDER BY u.id", [{
        "id": 1, "nombre": "Ana", "email": "ana@test.com", "rol": "admin", "activo": True,
        "limite_tokens": 20000, "tokens_usados": 0, "creado_en": datetime(2026, 11, 9)}])
    r = cliente.get("/usuarios", headers=cabeceras)
    assert r.status_code == 200 and r.json()[0]["email"] == "ana@test.com"


# ---------------------------------------------------------------- chat
def test_chat_valida_el_mensaje(cliente, con_sesion):
    assert cliente.post("/chat", json={"mensaje": ""}, headers=con_sesion()).status_code == 422


def test_chat_completo_responde_con_fuentes(cliente, bd, con_sesion, monkeypatch):
    cabeceras = con_sesion()
    bd.cuando("FROM servicios_ia WHERE codigo = 'chatbot_rag'", {"id": 1, "activo": True})
    bd.cuando("SUM(tokens_total)", {"total": 0})
    bd.cuando("INSERT INTO conversaciones", {"id": 5})
    bd.cuando("INSERT INTO mensajes", 1)
    bd.cuando("INSERT INTO consumo_tokens", 1)
    monkeypatch.setattr(chatbot, "recuperar", lambda consulta: [FRAGMENTO])
    monkeypatch.setattr(chatbot.llm, "completar", lambda m, **k: ("Visita Antigua [1].", 100, 40))

    r = cliente.post("/chat", json={"mensaje": "¿Qué hago en Antigua?"}, headers=cabeceras)

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["conversacion_id"] == 5
    assert cuerpo["fuentes"][0]["titulo"] == "Antigua Guatemala"
    assert cuerpo["tokens_consulta"] == 140


def test_chat_bloqueado_cuando_se_agota_el_limite(cliente, bd, con_sesion, monkeypatch):
    cabeceras = con_sesion(limite_tokens=1000)
    bd.cuando("FROM servicios_ia WHERE codigo = 'chatbot_rag'", {"id": 1, "activo": True})
    bd.cuando("SUM(tokens_total)", {"total": 1000})
    monkeypatch.setattr(chatbot.llm, "completar", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("No debía llamar al modelo")))

    r = cliente.post("/chat", json={"mensaje": "Hola"}, headers=cabeceras)
    assert r.status_code == 429
    assert "límite" in r.json()["detail"]


# ---------------------------------------------------------------- historial
def _conversacion(usuario_id):
    return {"id": 3, "titulo": "Antigua", "servicio_id": 1, "servicio": "Guía Chapín",
            "usuario_id": usuario_id, "usuario": "Otro", "creada_en": datetime(2026, 11, 9),
            "mensajes": 2, "tokens_total": 150}


def test_usuario_no_ve_conversaciones_ajenas(cliente, bd, con_sesion):
    cabeceras = con_sesion(id=1)
    bd.cuando("WHERE cv.id = %s", _conversacion(usuario_id=2))   # pertenece a otro usuario
    assert cliente.get("/historial/3", headers=cabeceras).status_code == 404


def test_admin_si_ve_conversaciones_ajenas(cliente, bd, con_sesion):
    cabeceras = con_sesion(id=1, rol="admin")
    bd.cuando("WHERE cv.id = %s", _conversacion(usuario_id=2))
    bd.cuando("FROM mensajes WHERE conversacion_id", [
        {"id": 1, "rol": "user", "contenido": "Hola", "fuentes": None, "creado_en": datetime(2026, 11, 9)}])
    r = cliente.get("/historial/3", headers=cabeceras)
    assert r.status_code == 200 and r.json()["lista_mensajes"][0]["contenido"] == "Hola"


def test_historial_del_usuario_siempre_se_filtra_por_su_id(cliente, bd, con_sesion):
    cabeceras = con_sesion(id=4)
    bd.cuando("FROM conversaciones cv", [])
    assert cliente.get("/historial", headers=cabeceras).status_code == 200
    _, sql, params = bd.llamadas_con("FROM conversaciones cv")[0]
    assert "cv.usuario_id = %s" in sql and params[0] == 4


# ---------------------------------------------------------------- reporte de consumo
FILAS_SERVICIO = [
    {"servicio_id": 1, "codigo": "chatbot_rag", "servicio": "Guía Chapín",
     "consultas": 2, "tokens_entrada": 100, "tokens_salida": 40, "tokens_total": 140},
    {"servicio_id": 2, "codigo": "planificador_ruta", "servicio": "Planificador de Ruta",
     "consultas": 1, "tokens_entrada": 300, "tokens_salida": 60, "tokens_total": 360},
]


def test_resumen_de_consumo_suma_y_calcula_lo_que_queda(cliente, bd, con_sesion):
    cabeceras = con_sesion(limite_tokens=1000)
    bd.cuando("FROM servicios_ia s LEFT JOIN consumo_tokens", FILAS_SERVICIO)
    r = cliente.get("/consumo/resumen", headers=cabeceras)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["consultas"] == 3
    assert cuerpo["tokens_usados"] == 500            # 140 + 360
    assert cuerpo["tokens_restantes"] == 500         # 1000 - 500
    assert cuerpo["limite_tokens"] == 1000


def test_resumen_nunca_muestra_tokens_restantes_negativos(cliente, bd, con_sesion):
    cabeceras = con_sesion(limite_tokens=100)
    bd.cuando("FROM servicios_ia s LEFT JOIN consumo_tokens", FILAS_SERVICIO)
    assert cliente.get("/consumo/resumen", headers=cabeceras).json()["tokens_restantes"] == 0


def test_usuario_normal_no_puede_ver_el_consumo_de_otro(cliente, con_sesion):
    r = cliente.get("/consumo/por-servicio?usuario_id=99", headers=con_sesion(id=1))
    assert r.status_code == 403


def test_admin_puede_ver_el_consumo_de_otro_usuario(cliente, bd, con_sesion):
    bd.cuando("FROM servicios_ia s LEFT JOIN consumo_tokens", FILAS_SERVICIO)
    r = cliente.get("/consumo/por-servicio?usuario_id=99", headers=con_sesion(id=1, rol="admin"))
    assert r.status_code == 200 and len(r.json()) == 2


def test_rango_de_fechas_invertido_da_400(cliente, con_sesion):
    r = cliente.get("/consumo/por-servicio?desde=2026-11-10&hasta=2026-11-01", headers=con_sesion())
    assert r.status_code == 400


def test_detalle_de_consumo_devuelve_una_fila_por_consulta(cliente, bd, con_sesion):
    """Es la misma fuente que lee Power BI: las columnas deben ser las esperadas."""
    cabeceras = con_sesion(rol="admin")
    bd.cuando("FROM consumo_tokens c JOIN usuarios", [{
        "id": 10, "fecha_hora": datetime(2026, 11, 9, 14, 30), "usuario_id": 1, "usuario": "Ana",
        "servicio_id": 1, "servicio": "Guía Chapín", "conversacion_id": 5,
        "tokens_entrada": 100, "tokens_salida": 40, "tokens_total": 140}])
    r = cliente.get("/consumo/detalle?limite=10", headers=cabeceras)
    assert r.status_code == 200
    fila = r.json()[0]
    assert fila["tokens_total"] == fila["tokens_entrada"] + fila["tokens_salida"]
    assert {"fecha_hora", "usuario", "servicio", "tokens_total"} <= set(fila)
