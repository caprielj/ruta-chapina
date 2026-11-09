import { useCallback, useEffect, useState } from 'react';
import { api } from '../../api';
import Modal from '../../componentes/Modal';

export default function Servicios() {
  const [lista, setLista] = useState([]);
  const [form, setForm] = useState(null);
  const [error, setError] = useState('');

  const cargar = useCallback(() => api('/servicios').then(setLista).catch((e) => setError(e.message)), []);
  useEffect(() => { cargar(); }, [cargar]);

  const alternar = async (s) => {
    setError('');
    try { await api(`/servicios/${s.id}`, { method: 'PUT', body: { activo: !s.activo } }); cargar(); } catch (e) { setError(e.message); }
  };

  const guardar = async (e) => {
    e.preventDefault();
    try { await api(`/servicios/${form.id}`, { method: 'PUT', body: { nombre: form.nombre, descripcion: form.descripcion } }); setForm(null); cargar(); }
    catch (err) { setError(err.message); }
  };

  return (
    <>
      <div className="encabezado"><h1>Servicios de IA</h1><p>Activa o desactiva cada servicio. Un servicio desactivado deja de responder a todos los usuarios.</p></div>
      {error && <div className="error">{error}</div>}
      <div className="rejilla dos">
        {lista.map((s) => (
          <div className="tarjeta" key={s.id} style={{ margin: 0 }}>
            <div className="fila"><h2 style={{ margin: 0 }}>{s.nombre}</h2><div className="sep" /><span className={'etiqueta' + (s.activo ? ' jade' : ' rojo')}>{s.activo ? 'Activo' : 'Desactivado'}</span></div>
            <p className="suave peq">Código: {s.codigo}</p>
            <p>{s.descripcion}</p>
            <div className="fila">
              <button className={'btn' + (s.activo ? ' peligro' : '')} onClick={() => alternar(s)}>{s.activo ? 'Desactivar' : 'Activar'}</button>
              <button className="btn sec" onClick={() => setForm({ id: s.id, nombre: s.nombre, descripcion: s.descripcion || '' })}>Editar texto</button>
            </div>
          </div>
        ))}
      </div>
      {form && (
        <Modal titulo="Editar servicio" onCerrar={() => setForm(null)}>
          <form onSubmit={guardar}>
            <div className="campo"><label>Nombre</label><input required minLength={2} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></div>
            <div className="campo"><label>Descripción</label><textarea value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></div>
            <div className="fila"><button className="btn">Guardar</button><button type="button" className="btn sec" onClick={() => setForm(null)}>Cancelar</button></div>
          </form>
        </Modal>
      )}
    </>
  );
}
