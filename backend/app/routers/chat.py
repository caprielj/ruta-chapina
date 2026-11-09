from fastapi import APIRouter, Depends

from .. import chatbot, rag_indice
from ..schemas import ChatEntrada, ChatSalida
from ..seguridad import solo_admin, usuario_actual

router = APIRouter(prefix="/chat", tags=["Chatbot RAG"])
router_rag = APIRouter(prefix="/rag", tags=["Chatbot RAG"])


@router.post("", response_model=ChatSalida)
def chat(datos: ChatEntrada, usuario: dict = Depends(usuario_actual)):
    """Envía una pregunta a la Guía Chapín. Sin conversacion_id abre una conversación nueva."""
    return chatbot.conversar(usuario, datos.mensaje, datos.conversacion_id)


@router_rag.post("/reindexar")
def reindexar(_admin: dict = Depends(solo_admin)):
    """El admin la ejecuta después de modificar destinos, actividades o platillos,
    para que el chatbot vea los cambios."""
    return rag_indice.reindexar()