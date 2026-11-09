import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from psycopg2.extras import Json

from . import consumo, db, herramientas, llm

MAX_RONDAS = 7   # máximo de vueltas del agente antes de forzar la respuesta final

# Ambos agentes comparten las mismas herramientas; cambia su misión (el prompt)
HERRAMIENTAS = ["buscar_destinos", "detalle_destinos", "consultar_clima", "calcular_distancia", "calcular_presupuesto"]

PROMPT_PLANIFICADOR = """Eres el Planificador de Ruta de Ruta Chapina, experto en viajes por Guatemala.
Obtienes TODOS los datos (destinos, precios, clima, distancias) con herramientas, nunca de memoria.
Proceso:
1. Entiende la solicitud (días, personas, presupuesto, intereses). Si falta algo, asume 3 días, 1 persona y sin tope de presupuesto, y dilo.
2. buscar_destinos según los intereses.
3. detalle_destinos de los 1 a 3 destinos elegidos.
4. consultar_clima de esos destinos.
5. Si son 2 o más destinos, calcular_distancia entre ellos.
6. calcular_presupuesto con los ids reales de las actividades elegidas.
7. Redacta el itinerario final.
Reglas: usa solo ids y precios que devolvieron las herramientas; si una herramienta falla, dilo; respeta el presupuesto y, si no alcanza, explícalo y propón lo más cercano.
Respuesta final en español y Markdown, concisa (máx. 350 palabras), con: ## Resumen, ## Itinerario (día por día, con una comida típica sugerida), ## Clima, ## Presupuesto (tabla), ## Recomendación.
Los precios son en quetzales (Q), aproximados y sin transporte."""

PROMPT_AJUSTE = """Eres el Ajustador de Plan de Ruta Chapina. Recibes un plan de viaje previo y un cambio (lluvia, menos presupuesto, otro interés...) y lo reajustas.
Obtienes TODOS los datos con herramientas, nunca de memoria.
Proceso:
1. Identifica qué cambia y qué partes del plan se ven afectadas.
2. Si el cambio es el clima, consultar_clima de los destinos del plan para confirmarlo.
3. Si hay que sustituir algo, buscar_destinos (usa presupuesto_diario_max si bajó el dinero) y detalle_destinos de las alternativas; con lluvia prefiere actividades cubiertas, culturales o gastronómicas.
4. calcular_presupuesto del plan ajustado.
5. Redacta el resultado.
Reglas: usa solo ids y precios de las herramientas; si una falla, dilo; conserva lo que no necesita cambiar.
Respuesta final en español y Markdown, concisa (máx. 350 palabras), con: ## Qué cambió y por qué, ## Plan ajustado (día por día), ## Presupuesto (antes y después si hay datos), ## Recomendación.
Los precios son en quetzales (Q), aproximados y sin transporte."""

PROMPTS = {"planificador_ruta": PROMPT_PLANIFICADOR, "ajuste_plan": PROMPT_AJUSTE}


def _sin_coordenadas(obj):
    """Quita lat/lon antes de enviar el resultado al modelo (ahorra tokens; son solo para el mapa)."""
    if isinstance(obj, dict):
        return {k: _sin_coordenadas(v) for k, v in obj.items() if k not in ("lat", "lon")}
    if isinstance(obj, list):
        return [_sin_coordenadas(v) for v in obj]
    return obj


def _resumir(nombre: str, res: dict) -> str:
    """Una línea legible por paso, para mostrar la línea de tiempo en la web."""
    if "error" in res:
        return f"Error: {res['error']}"
    if nombre in ("buscar_destinos", "detalle_destinos"):
        return ", ".join(d["nombre"] for d in res.get("destinos", [])) or res.get("nota", "Sin resultados")
    if nombre == "consultar_clima":
        return "Pronóstico de " + ", ".join(c["destino"] for c in res.get("clima", []))
    if nombre == "calcular_distancia":
        return "; ".join(f"{t['origen']} → {t['destino']}: {t['km']} km, {t['horas']} h" for t in res.get("tramos", []))
    if nombre == "calcular_presupuesto":
        return f"Total Q{res.get('total_gtq', 0)} para {res.get('personas', 1)} persona(s)"
    return "OK"


def _recolectar(nombre: str, res: dict, ctx: dict):
    """Guarda los datos estructurados que la web visualiza (mapa, clima, distancias, presupuesto)."""
    for d in res.get("destinos", []):
        ctx["destinos"][d["id"]] = {k: d[k] for k in ("id", "nombre", "departamento", "lat", "lon")}
    ctx["clima"].extend(res.get("clima", []))
    ctx["distancias"].extend(res.get("tramos", []) if nombre == "calcular_distancia" else [])
    if nombre == "calcular_presupuesto" and "total_gtq" in res:
        ctx["presupuesto"] = res


def correr_agente(codigo: str, usuario: dict, solicitud: str, plan_previo_id: int | None = None) -> dict:
    # 1) Servicio activo y límite de tokens (se verifica ANTES de gastar nada)
    servicio = db.uno("SELECT id, activo FROM servicios_ia WHERE codigo = %s", (codigo,))
    if not servicio or not servicio["activo"]:
        raise HTTPException(403, "Este servicio está desactivado")
    usados = consumo.verificar_limite(usuario)

    # 2) Mensaje inicial (el ajuste recibe además el plan anterior)
    hoy = datetime.now(timezone(timedelta(hours=-6))).strftime("%Y-%m-%d")  # hora de Guatemala
    contenido = f"SOLICITUD: {solicitud}"
    if codigo == "ajuste_plan":
        if plan_previo_id is not None:
            previo = db.uno(
                "SELECT resultado FROM resultados_agentes WHERE id = %s AND usuario_id = %s",
                (plan_previo_id, usuario["id"]),
            )
            if not previo or not previo["resultado"]:
                raise HTTPException(404, "Plan previo no encontrado")
            contenido = f"PLAN PREVIO:\n{previo['resultado']['respuesta'][:3000]}\n\nCAMBIO SOLICITADO: {solicitud}"
        else:
            contenido = f"No hay plan guardado; usa lo que describe el usuario.\nCAMBIO SOLICITADO: {solicitud}"

    mensajes = [
        {"role": "system", "content": PROMPTS[codigo] + f"\nFecha de hoy: {hoy}."},
        {"role": "user", "content": contenido},
    ]
    esquemas = [herramientas.ESQUEMAS[n] for n in HERRAMIENTAS]

    ctx = {"destinos": {}, "clima": [], "distancias": [], "presupuesto": None}
    pasos, t_in, t_out, respuesta = [], 0, 0, None

    # 3) Bucle del agente: el modelo pide herramientas, nosotros las ejecutamos y le devolvemos
    #    los resultados, hasta que responde con texto (la respuesta final)
    for _ in range(MAX_RONDAS):
        msg, a, b = llm.completar_agente(mensajes, esquemas)
        t_in, t_out = t_in + a, t_out + b
        if not msg.tool_calls:
            respuesta = (msg.content or "").strip()
            break

        # Registramos el turno del asistente con sus llamadas a herramientas
        mensajes.append({
            "role": "assistant", "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            try:
                argumentos = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                argumentos = {}
            res = herramientas.ejecutar(tc.function.name, argumentos)
            _recolectar(tc.function.name, res, ctx)
            pasos.append({"herramienta": tc.function.name, "argumentos": argumentos,
                          "resumen": _resumir(tc.function.name, res)})
            mensajes.append({
                "role": "tool", "tool_call_id": tc.id,
                "content": json.dumps(_sin_coordenadas(res), ensure_ascii=False, separators=(",", ":")),
            })

    if not respuesta:
        # Se acabaron las vueltas (o respondió vacío): pedimos la respuesta final sin herramientas
        mensajes.append({"role": "user", "content": "Con lo que ya tienes, redacta ahora la respuesta final."})
        msg, a, b = llm.completar_agente(mensajes, None)
        t_in, t_out = t_in + a, t_out + b
        respuesta = (msg.content or "").strip() or "No pude completar la solicitud. Intenta de nuevo."

    # 4) Guardado: resultado + pasos + consumo de tokens
    resultado = {
        "respuesta": respuesta, "destinos": list(ctx["destinos"].values()),
        "clima": ctx["clima"], "distancias": ctx["distancias"], "presupuesto": ctx["presupuesto"],
    }
    fila = db.uno(
        """INSERT INTO resultados_agentes (usuario_id, servicio_id, solicitud, pasos, resultado)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (usuario["id"], servicio["id"], solicitud, Json(pasos), Json(resultado)),
    )
    consumo.registrar(usuario["id"], servicio["id"], None, t_in, t_out)

    return {
        "resultado_id": fila["id"], "respuesta": respuesta, "pasos": pasos,
        "destinos": resultado["destinos"], "clima": resultado["clima"],
        "distancias": resultado["distancias"], "presupuesto": resultado["presupuesto"],
        "tokens_consulta": t_in + t_out,
        "tokens_restantes": max(usuario["limite_tokens"] - usados - t_in - t_out, 0),
    }