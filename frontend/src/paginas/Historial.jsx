import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import Md from '../componentes/Md';
import Modal from '../componentes/Modal';

const hora = (s) => (s || '').slice(0, 16).replace('T', ' ');

export default function Historial() {
  const { user } = useAuth();
  const esAdmin = user.rol === 'admin';
  const navegar = useNavigate();
  const [pestana, setPestana] = useState('chat');
  const [servicios, setServicios] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [f, setF] = useState({ servicio_id: '', usuario_id: '', desde: '', hasta: '' });
  const [convs, setConvs] = useState([]);
  const [resultados, setResultados] = useState([]);
  const [detalle, setDetalle] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    api('/servicios').then(setServicios).catch(() => {});
    if (esAdmin) api('/usuarios').then(setUsuarios).catch(() => {});
  }, [esAdmin]);

  // Vuelve a consultar cuando cambia la pestaña o algún filtro
  const cargar = useCallback(async () => {
    setError(''); setCargando(true);
    try {
      if (pestana === 'chat') {
        setConvs(await api('/historial', { params: { ...f, limite: 200 } }));
      } else {
        // Los resultados de agentes no filtran por fecha en la API; se filtra aquí
        let r = await api('/agentes/resultados', { params: { servicio_id: f.servicio_id, usuario_id: f.usuario_id, limite: 200 } });
        if (f.desde) r = r.filter((x) => x.creado_en.slice(0, 10) >= f.desde);
        if (f.hasta) r = r.filter((x) => x.creado_en.slice(0, 10) <= f.hasta);
        setResultados(r);
      }
    } catch (e) { setError(e.message); }
    finally { setCargando(false); }
  }, [pestana, f]);
  useEffect(() => { cargar(); }, [cargar]);

  const abrir = async (id) => {
    try { setDetalle(await api(`/historial/${id}`)); } catch (e) { setError(e.message); }
  };

  const cambiar = (k) => (e) => setF({ ...f, [k]: e.target.value });
  // Cada pestaña solo ofrece los servicios que le corresponden
  const serviciosPestana = servicios.filter((s) => (pestana === 'chat') === (s.codigo === 'chatbot_rag'));

  return (
    <>
      <div className="encabezado"><h1>Historial</h1><p>{esAdmin ? 'Todas las conversaciones y resultados de la plataforma.' : 'Tus conversaciones con la Guía Chapín y los resultados de tus agentes.'}</p></div>

      <div className="pestanas">
        <button className={pestana === 'chat' ? 'activa' : ''} onClick={() => { setPestana('chat'); setF({ ...f, servicio_id: '' }); }}>Conversaciones</button>
        <button className={pestana === 'agentes' ? 'activa' : ''} onClick={() => { setPestana('agentes'); setF({ ...f, servicio_id: '' }); }}>Resultados de agentes</button>
      </div>

      <div className="filtros">
        <label>Servicio<select value={f.servicio_id} onChange={cambiar('servicio_id')}><option value="">Todos</option>{serviciosPestana.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}</select></label>
        {esAdmin && <label>Usuario<select value={f.usuario_id} onChange={cambiar('usuario_id')}><option value="">Todos</option>{usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}</select></label>}
        <label>Desde<input type="date" value={f.desde} onChange={cambiar('desde')} /></label>
        <label>Hasta<input type="date" value={f.hasta} onChange={cambiar('hasta')} /></label>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="tabla-caja">
        {pestana === 'chat' ? (
          <table className="tabla">
            <thead><tr><th>Fecha</th>{esAdmin && <th>Usuario</th>}<th>Conversación</th><th className="num">Mensajes</th><th className="num">Tokens</th></tr></thead>
            <tbody>
              {convs.map((c) => (
                <tr key={c.id} className="fila-click" onClick={() => abrir(c.id)}>
                  <td>{hora(c.creada_en)}</td>{esAdmin && <td>{c.usuario}</td>}<td>{c.titulo}</td><td className="num">{c.mensajes}</td><td className="num">{c.tokens_total.toLocaleString('es-GT')}</td>
                </tr>
              ))}
              {!cargando && convs.length === 0 && <tr><td colSpan={5} className="suave">No hay conversaciones con esos filtros.</td></tr>}
            </tbody>
          </table>
        ) : (
          <table className="tabla">
            <thead><tr><th>Fecha</th>{esAdmin && <th>Usuario</th>}<th>Servicio</th><th>Solicitud</th></tr></thead>
            <tbody>
              {resultados.map((r) => (
                <tr key={r.id} className="fila-click" onClick={() => navegar(`/resultado/${r.id}`)}>
                  <td>{hora(r.creado_en)}</td>{esAdmin && <td>{r.usuario}</td>}<td>{r.servicio}</td><td>{r.solicitud.length > 110 ? r.solicitud.slice(0, 110) + '…' : r.solicitud}</td>
                </tr>
              ))}
              {!cargando && resultados.length === 0 && <tr><td colSpan={4} className="suave">No hay resultados con esos filtros.</td></tr>}
            </tbody>
          </table>
        )}
      </div>

      {detalle && (
        <Modal titulo={detalle.titulo} onCerrar={() => setDetalle(null)}>
          <p className="suave peq">{detalle.usuario} · {hora(detalle.creada_en)} · {detalle.tokens_total.toLocaleString('es-GT')} tokens</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {detalle.lista_mensajes.map((m) => (
              <div key={m.id} className={`burbuja ${m.rol}`} style={{ maxWidth: '100%' }}>
                {m.rol === 'user' ? m.contenido : <Md>{m.contenido}</Md>}
                {m.fuentes?.length > 0 && <div className="fuentes">{m.fuentes.map((x, j) => <span key={j} className="etiqueta jade"><b>[{j + 1}]</b>{x.titulo}</span>)}</div>}
              </div>
            ))}
          </div>
          {detalle.usuario_id === user.id && (
            <div style={{ marginTop: 16 }}><button className="btn" onClick={() => navegar(`/chat?conv=${detalle.id}`)}>Continuar esta conversación</button></div>
          )}
        </Modal>
      )}
    </>
  );
}
