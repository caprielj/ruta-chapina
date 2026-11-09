import { useCallback, useEffect, useState } from 'react';
import { api } from '../../api';
import Modal from '../../componentes/Modal';

/**
 * CRUD de las entidades que alimentan los servicios de IA: destinos, actividades y platillos.
 * Cada entidad se describe con su configuración: la pantalla (tabla + formulario) se genera sola.
 *   t: tipo de campo (texto | area | num | bool | destino)   req: obligatorio
 */
const ENTIDADES = {
  destinos: {
    titulo: 'Destinos', ruta: '/destinos', columnas: ['nombre', 'departamento', 'categoria', 'costo_diario_gtq', 'activo'],
    vacio: { nombre: '', departamento: '', region: '', categoria: 'cultural', descripcion: '', latitud: '', longitud: '', costo_diario_gtq: 0, mejor_epoca: '', imagen_url: '', activo: true },
    campos: [
      { k: 'nombre', l: 'Nombre', t: 'texto', req: 1 }, { k: 'departamento', l: 'Departamento', t: 'texto', req: 1 },
      { k: 'region', l: 'Región', t: 'texto', req: 1 }, { k: 'categoria', l: 'Categoría', t: 'texto', req: 1 },
      { k: 'descripcion', l: 'Descripción', t: 'area', req: 1 },
      { k: 'latitud', l: 'Latitud', t: 'num', paso: 'any', req: 1 }, { k: 'longitud', l: 'Longitud', t: 'num', paso: 'any', req: 1 },
      { k: 'costo_diario_gtq', l: 'Costo diario (Q)', t: 'num', paso: 1, req: 1 }, { k: 'mejor_epoca', l: 'Mejor época', t: 'texto' },
      { k: 'imagen_url', l: 'URL de imagen', t: 'texto' }, { k: 'activo', l: 'Activo', t: 'bool' },
    ],
  },
  actividades: {
    titulo: 'Actividades', ruta: '/actividades', columnas: ['nombre', 'destino_id', 'tipo', 'duracion_horas', 'costo_gtq', 'activo'],
    vacio: { destino_id: '', nombre: '', tipo: 'cultural', descripcion: '', duracion_horas: 2, costo_gtq: 0, activo: true },
    campos: [
      { k: 'destino_id', l: 'Destino', t: 'destino', req: 1 }, { k: 'nombre', l: 'Nombre', t: 'texto', req: 1 }, { k: 'tipo', l: 'Tipo', t: 'texto', req: 1 },
      { k: 'descripcion', l: 'Descripción', t: 'area', req: 1 },
      { k: 'duracion_horas', l: 'Duración (horas)', t: 'num', paso: 0.5, req: 1 }, { k: 'costo_gtq', l: 'Costo (Q)', t: 'num', paso: 1, req: 1 }, { k: 'activo', l: 'Activa', t: 'bool' },
    ],
  },
  platillos: {
    titulo: 'Platillos', ruta: '/platillos', columnas: ['nombre', 'tipo', 'departamento_origen', 'vegetariano', 'activo'],
    vacio: { nombre: '', tipo: 'plato fuerte', departamento_origen: 'Nacional', region: 'Nacional', descripcion: '', ingredientes: '', vegetariano: false, activo: true },
    campos: [
      { k: 'nombre', l: 'Nombre', t: 'texto', req: 1 }, { k: 'tipo', l: 'Tipo (plato fuerte, bebida, postre, antojito)', t: 'texto', req: 1 },
      { k: 'departamento_origen', l: 'Departamento de origen (o "Nacional")', t: 'texto', req: 1 }, { k: 'region', l: 'Región', t: 'texto', req: 1 },
      { k: 'descripcion', l: 'Descripción', t: 'area', req: 1 }, { k: 'ingredientes', l: 'Ingredientes', t: 'area', req: 1 },
      { k: 'vegetariano', l: 'Es vegetariano', t: 'bool' }, { k: 'activo', l: 'Activo', t: 'bool' },
    ],
  },
};

export default function Catalogo() {
  const [clave, setClave] = useState('destinos');
  const cfg = ENTIDADES[clave];
  const [filas, setFilas] = useState([]);
  const [destinos, setDestinos] = useState([]);
  const [form, setForm] = useState(null);
  const [editId, setEditId] = useState(null);
  const [error, setError] = useState('');
  const [errorForm, setErrorForm] = useState('');
  const [aviso, setAviso] = useState('');
  const [pendiente, setPendiente] = useState(false); // hay cambios que el chatbot aún no ve
  const [indexando, setIndexando] = useState(false);

  const cargar = useCallback(async () => {
    setError('');
    try {
      setFilas(await api(cfg.ruta, { params: { limite: 500 } }));
      setDestinos(await api('/destinos', { params: { limite: 500 } }));
    } catch (e) { setError(e.message); }
  }, [cfg.ruta]);
  useEffect(() => { setFilas([]); cargar(); }, [cargar]);

  const nombreDestino = (id) => destinos.find((d) => d.id === id)?.nombre || id;
  const abrirNuevo = () => { setEditId(null); setForm({ ...cfg.vacio }); setErrorForm(''); };
  const abrirEditar = (fila) => {
    const base = {};
    cfg.campos.forEach((c) => { base[c.k] = fila[c.k] ?? ''; });
    setEditId(fila.id); setForm(base); setErrorForm('');
  };

  // Convierte lo escrito en el formulario al formato que espera la API
  const preparar = () => {
    const body = {};
    cfg.campos.forEach((c) => {
      const v = form[c.k];
      if (c.t === 'num' || c.t === 'destino') body[c.k] = Number(v);
      else if (c.t === 'bool') body[c.k] = !!v;
      else { const s = String(v ?? '').trim(); body[c.k] = s === '' && !c.req ? null : s; } // opcional vacío -> null
    });
    return body;
  };

  const guardar = async (e) => {
    e.preventDefault(); setErrorForm('');
    try {
      const body = preparar();
      if (editId) await api(`${cfg.ruta}/${editId}`, { method: 'PUT', body });
      else await api(cfg.ruta, { method: 'POST', body });
      setForm(null); setPendiente(true); cargar();
    } catch (err) { setErrorForm(err.message); }
  };

  const borrar = async (fila) => {
    if (!window.confirm(`¿Eliminar "${fila.nombre}"? No se puede deshacer.`)) return;
    try { await api(`${cfg.ruta}/${fila.id}`, { method: 'DELETE' }); setPendiente(true); cargar(); } catch (e) { setError(e.message); }
  };

  const reindexar = async () => {
    setIndexando(true); setAviso(''); setError('');
    try {
      const r = await api('/rag/reindexar', { method: 'POST' });
      setAviso(`Chatbot actualizado: ${r.indexados} documentos indexados (${r.destinos} destinos, ${r.actividades} actividades, ${r.platillos} platillos).`);
      setPendiente(false);
    } catch (e) { setError(e.message); }
    finally { setIndexando(false); }
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
  const mostrar = (fila, col) => {
    const v = fila[col];
    if (typeof v === 'boolean') return <span className={'etiqueta' + (v ? ' jade' : '')}>{v ? 'sí' : 'no'}</span>;
    return col === 'destino_id' ? nombreDestino(v) : String(v);
  };

  return (
    <>
      <div className="encabezado fila">
        <div><h1>Catálogo y datos</h1><p>Administra los datos que alimentan al chatbot y a los agentes.</p></div>
        <div className="sep" /><button className="btn" onClick={abrirNuevo}>Agregar</button>
      </div>

      <div className={pendiente ? 'tarjeta' : 'tarjeta'} style={pendiente ? { borderColor: 'var(--maiz)', borderWidth: 2 } : {}}>
        <div className="fila">
          <div style={{ flex: 1, minWidth: 220 }}>
            <b>Actualizar el conocimiento del chatbot</b>
            <div className="suave peq">{pendiente ? 'Hiciste cambios: ejecuta la actualización para que la Guía Chapín los vea.' : 'Después de agregar, editar o borrar datos, vuelve a indexar para que el chatbot los vea.'}</div>
          </div>
          <button className="btn" onClick={reindexar} disabled={indexando}>{indexando ? 'Indexando (puede tardar)…' : 'Reindexar chatbot'}</button>
        </div>
      </div>

      {aviso && <div className="exito">{aviso}</div>}
      {error && <div className="error">{error}</div>}

      <div className="pestanas">
        {Object.entries(ENTIDADES).map(([k, e]) => <button key={k} className={k === clave ? 'activa' : ''} onClick={() => setClave(k)}>{e.titulo}</button>)}
      </div>

      <div className="tabla-caja">
        <table className="tabla">
          <thead><tr>{cfg.columnas.map((c) => <th key={c}>{c.replace(/_/g, ' ')}</th>)}<th /></tr></thead>
          <tbody>
            {filas.map((fila) => (
              <tr key={fila.id}>
                {cfg.columnas.map((c) => <td key={c}>{mostrar(fila, c)}</td>)}
                <td className="num"><button className="btn sec mini" onClick={() => abrirEditar(fila)}>Editar</button>{' '}<button className="btn peligro mini" onClick={() => borrar(fila)}>Eliminar</button></td>
              </tr>
            ))}
            {filas.length === 0 && <tr><td colSpan={cfg.columnas.length + 1} className="suave">Sin registros.</td></tr>}
          </tbody>
        </table>
      </div>

      {form && (
        <Modal titulo={(editId ? 'Editar ' : 'Agregar ') + cfg.titulo.toLowerCase()} onCerrar={() => setForm(null)}>
          <form onSubmit={guardar}>
            {errorForm && <div className="error">{errorForm}</div>}
            {cfg.campos.map((c) => (
              <div key={c.k} className={'campo' + (c.t === 'bool' ? ' check' : '')}>
                {c.t === 'bool' ? (
                  <><input id={c.k} type="checkbox" checked={!!form[c.k]} onChange={set(c.k)} /><label htmlFor={c.k}>{c.l}</label></>
                ) : (
                  <>
                    <label htmlFor={c.k}>{c.l}</label>
                    {c.t === 'area' && <textarea id={c.k} required={!!c.req} value={form[c.k]} onChange={set(c.k)} />}
                    {c.t === 'texto' && <input id={c.k} required={!!c.req} value={form[c.k]} onChange={set(c.k)} />}
                    {c.t === 'num' && <input id={c.k} type="number" step={c.paso} required={!!c.req} value={form[c.k]} onChange={set(c.k)} />}
                    {c.t === 'destino' && (
                      <select id={c.k} required value={form[c.k]} onChange={set(c.k)}>
                        <option value="">— Elige un destino —</option>
                        {destinos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
                      </select>
                    )}
                  </>
                )}
              </div>
            ))}
            <div className="fila"><button className="btn">Guardar</button><button type="button" className="btn sec" onClick={() => setForm(null)}>Cancelar</button></div>
          </form>
        </Modal>
      )}
    </>
  );
}
