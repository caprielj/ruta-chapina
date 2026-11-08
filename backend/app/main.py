# Importamos FastAPI, el framework que construye la API y genera Swagger automáticamente
from fastapi import FastAPI

# Creamos la aplicación. El título y la versión aparecen en la documentación /docs
app = FastAPI(title="Ruta Chapina API", version="0.1.0")


# Endpoint de prueba: responde a GET /salud
# Lo usaremos también para saber si el servidor en la nube está despierto
@app.get("/salud")
def salud():
    return {"estado": "ok", "proyecto": "Ruta Chapina"}