"""Muestra qué tan parecidas son algunas preguntas a tus documentos, para elegir RAG_UMBRAL.
Uso (desde la carpeta backend, con el entorno virtual activo):  python -m scripts.calibrar_umbral
Regla: el umbral debe quedar ENTRE la mejor similitud de las preguntas fuera de tema y la peor
de las preguntas de turismo."""
from app import config, db, embeddings

PRUEBAS = [
    ("DENTRO", "¿Qué puedo hacer en Antigua Guatemala?"),
    ("DENTRO", "¿Qué es el kak'ik?"),
    ("DENTRO", "lugares de aventura con volcanes"),
    ("DENTRO", "¿Dónde puedo comer algo vegetariano?"),
    ("FUERA ", "¿Cuál es la capital de Francia?"),
    ("FUERA ", "cómo programar en Python"),
    ("FUERA ", "quién ganó el mundial de 2010"),
]

if __name__ == "__main__":
    print(f"Umbral actual (RAG_UMBRAL): {config.RAG_UMBRAL}\n")
    for tipo, pregunta in PRUEBAS:
        v = embeddings.a_literal(embeddings.embed_uno(pregunta))
        filas = db.todos(
            """SELECT titulo, 1 - (embedding <=> %s::vector) AS similitud
               FROM documentos_rag WHERE embedding IS NOT NULL
               ORDER BY embedding <=> %s::vector LIMIT 1""", (v, v))
        mejor = filas[0]
        print(f"[{tipo}] {float(mejor['similitud']):.2f}  {pregunta}   -> {mejor['titulo']}")
