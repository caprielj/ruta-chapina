from fastapi import HTTPException
from psycopg2.extras import Json

from . import config, consumo, db, embeddings, llm

FRASE_SIN_INFO = "No tengo información suficiente"

RESPUESTA_SIN_INFO = (
    f"{FRASE_SIN_INFO} sobre eso en mi base de datos. Puedo ayudarte con destinos, actividades "
    "y gastronomía de Guatemala; por ejemplo: «¿Qué puedo hacer en Antigua?» o «¿Qué es el kak’ik?»."
)

PROMPT_SISTEMA = """Eres "Guía Chapín", un guía local de turismo y gastronomía de Guatemala.
Reglas:
1. Responde SOLO con la información del CONTEXTO que se te da. No inventes datos, precios, horarios ni lugares que no estén ahí.
2. Si el contexto no alcanza para responder bien, di claramente "No tengo información suficiente" sobre lo que falta.
3. Cita las fuentes con su número entre corchetes, por ejemplo [1] o [2][3].
4. Responde en español, con tono cercano y amable (trata de tú), con un toque guatemalteco suave y sin exagerar.
5. Sé breve: máximo unas 150 palabras, salvo que te pidan más detalle.
6. Los precios están en quetzales (Q) y son aproximados.
7. Usa el historial de la conversación para entender preguntas de seguimiento."""


def recuperar(consulta: str) -> list[dict]:
    """Búsqueda semántica: devuelve los fragmentos más parecidos a la consulta que superan el umbral."""
    vector = embeddings.a_literal(embeddings.embed_uno(consulta))
    filas = db.todos(
        """SELECT fuente_tabla, fuente_id, titulo, contenido,
                  1 - (embedding <=> %s::vector) AS similitud   -- <=> es distancia coseno
           FROM documentos_rag
           WHERE embedding IS NOT NULL
           ORDER BY embedding <=> %s::vector
           LIMIT %s""",
        (vector, vector, config.RAG_TOP_K),
    )
    return [f for f in filas if f["similitud"] >= config.RAG_UMBRAL]


def conversar(usuario: dict, mensaje: str, conversacion_id) -> dict:
    # 1) El servicio debe existir y estar activado por el administrador
    servicio = db.uno("SELECT id, activo FROM servicios_ia WHERE codigo = 'chatbot_rag'")
    if not servicio or not servicio["activo"]:
        raise HTTPException(403, "El servicio de chatbot está desactivado")

    # 2) Control de consumo: se verifica ANTES de gastar tokens
    usados = consumo.verificar_limite(usuario)

    # 3) Memoria: si continúa una conversación, cargamos sus últimos mensajes
    historial = []
    if conversacion_id is not None:
        conv = db.uno(
            "SELECT id FROM conversaciones WHERE id = %s AND usuario_id = %s AND servicio_id = %s",
            (conversacion_id, usuario["id"], servicio["id"]),
        )
        if not conv:
            raise HTTPException(404, "Conversación no encontrada")
        historial = db.todos(
            """SELECT rol, contenido FROM (
                   SELECT id, rol, contenido FROM mensajes
                   WHERE conversacion_id = %s ORDER BY id DESC LIMIT %s) t
               ORDER BY id""",
            (conversacion_id, config.MEMORIA_MENSAJES),
        )

    # 4) Recuperación. Se une la pregunta anterior del usuario para que un seguimiento
    #    como "¿y cuánto cuesta?" siga encontrando el tema del que se hablaba.
    previas = [m["contenido"] for m in historial if m["rol"] == "user"]
    consulta = (previas[-1] + " " if previas else "") + mensaje
    fragmentos = recuperar(consulta)

    # 5) Generación
    if not fragmentos:
        # Sin contexto relevante no llamamos al modelo: ahorra tokens y evita que invente
        respuesta, t_in, t_out, suficiente = RESPUESTA_SIN_INFO, 0, 0, False
    else:
        contexto = "\n\n".join(
            f"[{i}] {f['titulo']} ({f['fuente_tabla']} #{f['fuente_id']}): {f['contenido']}"
            for i, f in enumerate(fragmentos, start=1)
        )
        mensajes_llm = [{"role": "system", "content": PROMPT_SISTEMA}]
        mensajes_llm += [{"role": m["rol"], "content": m["contenido"]} for m in historial]
        mensajes_llm.append({"role": "user", "content": f"CONTEXTO:\n{contexto}\n\nPREGUNTA: {mensaje}"})
        respuesta, t_in, t_out = llm.completar(mensajes_llm)
        suficiente = FRASE_SIN_INFO.lower() not in respuesta.lower()

    fuentes = (
        [
            {"tabla": f["fuente_tabla"], "id": f["fuente_id"], "titulo": f["titulo"],
             "puntaje": round(float(f["similitud"]), 2)}
            for f in fragmentos
        ]
        if suficiente else []
    )

    # 6) Registro automático en la BD (solo si todo salió bien)
    if conversacion_id is None:
        conv = db.uno(
            "INSERT INTO conversaciones (usuario_id, servicio_id, titulo) VALUES (%s, %s, %s) RETURNING id",
            (usuario["id"], servicio["id"], mensaje[:60]),
        )
        conversacion_id = conv["id"]
    db.ejecutar(
        "INSERT INTO mensajes (conversacion_id, rol, contenido) VALUES (%s, 'user', %s)",
        (conversacion_id, mensaje),
    )
    db.ejecutar(
        "INSERT INTO mensajes (conversacion_id, rol, contenido, fuentes) VALUES (%s, 'assistant', %s, %s)",
        (conversacion_id, respuesta, Json(fuentes)),
    )
    consumo.registrar(usuario["id"], servicio["id"], conversacion_id, t_in, t_out)

    return {
        "conversacion_id": conversacion_id,
        "respuesta": respuesta,
        "fuentes": fuentes,
        "suficiente_info": suficiente,
        "tokens_consulta": t_in + t_out,
        "tokens_restantes": max(usuario["limite_tokens"] - usados - t_in - t_out, 0),
    }