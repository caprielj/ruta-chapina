import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import Md from '../componentes/Md';
import { sellar } from '../sellos';

const SUGERENCIAS = ['¿Qué puedo hacer en Antigua Guatemala?', '¿Qué es el kak’ik?', 'Quiero un lugar con aguas termales', '¿Qué platillos son vegetarianos?'];

export default function Chat() {
  const { user, refrescar } = useAuth();
  const [params, setParams] = useSearchParams();
  const [mensajes, setMensajes] = useState([]);
  const [convId, setConvId] = useState(null);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  const fin = useRef(null);

  // Si venimos del historial (?conv=ID), cargamos esa conversación para continuarla
  const convUrl = params.get('conv');
  useEffect(() => {
    if (!convUrl) return;
    api(`/historial/${convUrl}`)
      .then((c) => {
        setConvId(c.id);
        setMensajes(c.lista_mensajes.map((m) => ({ rol: m.rol, contenido: m.contenido, fuentes: m.fuentes || [], suficiente: !!(m.fuentes && m.fuentes.length) })));
      })
      .catch((e) => setError(e.message));
  }, [convUrl]);

  // Baja automáticamente al último mensaje
  useEffect(() => { fin.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [mensajes, enviando]);

  const nueva = () => { setMensajes([]); setConvId(null); setError(''); if (convUrl) setParams({}); };

  const enviar = async (pregunta) => {
    const msg = (pregunta ?? texto).trim();
    if (!msg || enviando) return;
    setError(''); setTexto(''); setEnviando(true);
    setMensajes((m) => [...m, { rol: 'user', contenido: msg }]);
    try {
      const r = await api('/chat', { method: 'POST', body: { mensaje: msg, conversacion_id: convId } });
      setConvId(r.conversacion_id);
      setMensajes((m) => [...m, { rol: 'assistant', contenido: r.respuesta, fuentes: r.fuentes, suficiente: r.suficiente_info }]);
      // Cada destino consultado queda sellado en el pasaporte
      sellar(user.id, r.fuentes.filter((f) => f.tabla === 'destinos').map((f) => ({ id: f.id, nombre: f.titulo })));
      refrescar(); // actualiza el medidor de tokens
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="chat">
      <div className="fila" style={{ marginBottom: 10 }}>
        <div><h1 style={{ margin: 0 }}>Guía Chapín</h1><span className="suave peq">Responde con la información guardada en la base de datos de Ruta Chapina</span></div>
        <div className="sep" />
        <button className="btn sec" onClick={nueva}>Nueva conversación</button>
      </div>

      <div className="chat-hilo">
        {mensajes.length === 0 && !enviando && (
          <div className="tarjeta">
            <h2>¡Hola, aquí tu guía!</h2>
            <p className="suave">Pregúntame por destinos, actividades o comida típica de Guatemala. Si no tengo el dato, te lo diré con franqueza.</p>
            <div className="sugerencias">
              {SUGERENCIAS.map((s) => <button key={s} onClick={() => enviar(s)}>{s}</button>)}
            </div>
          </div>
        )}

        {mensajes.map((m, i) => (
          <div key={i} className={`burbuja ${m.rol}` + (m.rol === 'assistant' && m.suficiente === false ? ' sin-info' : '')}>
            {m.rol === 'user' ? m.contenido : <Md>{m.contenido}</Md>}
            {m.rol === 'assistant' && m.suficiente === false && (
              <div style={{ marginTop: 8 }}><span className="etiqueta rojo">Sin información suficiente en la base de datos</span></div>
            )}
            {m.rol === 'assistant' && m.fuentes?.length > 0 && (
              <div className="fuentes">
                <span className="peq suave">Fuentes:</span>
                {m.fuentes.map((f, j) => (
                  <span key={j} className="etiqueta jade" title={`Similitud ${f.puntaje}`}><b>[{j + 1}]</b>{f.titulo} · {f.tabla}</span>
                ))}
              </div>
            )}
          </div>
        ))}

        {enviando && <div className="burbuja assistant"><span className="puntos"><span /><span /><span /></span></div>}
        {error && <div className="error" role="alert">{error}</div>}
        <div ref={fin} />
      </div>

      <form className="chat-entrada" onSubmit={(e) => { e.preventDefault(); enviar(); }}>
        <textarea
          rows={1} value={texto} placeholder="Escribe tu pregunta…" maxLength={1000}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(); } }}
        />
        <button className="btn" disabled={enviando || !texto.trim()}>Enviar</button>
      </form>
    </div>
  );
}
