from ..crud import crear_router_crud
from ..schemas import (ActividadIn, ActividadOut, DestinoIn, DestinoOut,
                       PlatilloIn, PlatilloOut)

# Un CRUD completo por entidad, con una sola línea cada una
router_destinos = crear_router_crud("/destinos", "destinos", DestinoIn, DestinoOut, "Destinos")
router_actividades = crear_router_crud("/actividades", "actividades", ActividadIn, ActividadOut, "Actividades")
router_platillos = crear_router_crud("/platillos", "platillos", PlatilloIn, PlatilloOut, "Platillos")