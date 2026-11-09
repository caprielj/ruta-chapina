import psycopg2
from psycopg2.extras import RealDictCursor   # devuelve las filas como diccionarios
from psycopg2.pool import ThreadedConnectionPool

from . import config

_pool = None  # se crea la primera vez que se necesita


def _obtener_pool():
    """Crea el pool de conexiones una sola vez (máximo 5, suficiente para el plan gratuito)."""
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(
            1, 5, config.DATABASE_URL, sslmode="require", connect_timeout=10
        )
    return _pool


def _correr(consulta, params=None, modo="todos"):
    """Ejecuta una consulta. Si la conexión estaba caída (pasa tras inactividad), reintenta una vez."""
    pool = _obtener_pool()
    for intento in (1, 2):
        conn = pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(consulta, params)
                if modo == "todos":
                    resultado = cur.fetchall()
                elif modo == "uno":
                    resultado = cur.fetchone()
                else:                      # modo "ejecutar": devolvemos cuántas filas afectó
                    resultado = cur.rowcount
            conn.commit()
            pool.putconn(conn)
            return resultado
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            pool.putconn(conn, close=True)  # descartamos la conexión rota
            if intento == 2:
                raise
        except Exception:
            conn.rollback()                 # deshacemos cambios a medias
            pool.putconn(conn)
            raise


def todos(consulta, params=None):
    """SELECT que devuelve una lista de filas."""
    return _correr(consulta, params, "todos")


def uno(consulta, params=None):
    """SELECT/INSERT...RETURNING que devuelve una sola fila (o None)."""
    return _correr(consulta, params, "uno")


def ejecutar(consulta, params=None):
    """UPDATE/DELETE: devuelve el número de filas afectadas."""
    return _correr(consulta, params, "ejecutar")