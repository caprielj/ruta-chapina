import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import Mapa from '../componentes/Mapa';
import Modal from '../componentes/Modal';
import { sellar } from '../sellos';

const claseCat = (c) => 'cat-' + (['cultural', 'naturaleza', 'aventura', 'arqueología', 'playa', 'gastronomía', 'religioso'].includes(c) ? c : 'otro');

export default function Explorar() {
  const { user } = useAuth();
  const navegar = useNavigate();
  const [destinos, setDestinos] = useState([]);
  const [actividades, setActividades] = useState([]);
  const [platillos, setPlatillos] = useState([]);
  const [q, setQ] = useState('');
  const [cat, setCat] = useState('');
  const [abierto, setAbierto] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api('/destinos', { params: { limite: 500 } }), api('/actividades', { params: { limite: 500 } }), api('/platillos', { params: { limite: 500 } })])
      .then(([d, a, p]) => { setDestinos(d); setActividades(a); setPlatillos(p); })
      .catch((e) => setError(e.message));
  }, []);

  const categorias = useMemo(() => [...new Set(destinos.map((d) => d.categoria))].sort(), [destinos]);
  const visibles = useMemo(() => destinos.filter((d) =>
    (!cat || d.categoria === cat) && (!q || `${d.nombre} ${d.departamento} ${d.descripcion}`.toLowerCase().includes(q.toLowerCase()))), [destinos, q, cat]);
  const puntos = useMemo(() => visibles.map((d) => ({ id: d.id, nombre: d.nombre, sub: d.departamento, lat: d.latitud, lon: d.longitud })), [visibles]);

  // Al abrir un destino se "sella" en el pasaporte
  const abrir = (d) => { setAbierto(d); sellar(user.id, [{ id: d.id, nombre: d.nombre }]); };
  const elegirPorMapa = (p) => { const d = destinos.find((x) => x.id === p.id); if (d) abrir(d); };

  return (
    <>
      <div className="encabezado"><h1>Destinos y sabores</h1><p>Explora el catálogo de Ruta Chapina. Al abrir un destino, queda sellado en tu pasaporte.</p></div>
      {error && <div className="error">{error}</div>}

      <div className="filtros">
        <label>Buscar<input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Atitlán, volcán, café…" /></label>
        <label>Categoría<select value={cat} onChange={(e) => setCat(e.target.value)}><option value="">Todas</option>{categorias.map((c) => <option key={c}>{c}</option>)}</select></label>
        <span className="suave peq">{visibles.length} destino(s)</span>
      </div>

      <div className="tarjeta"><Mapa puntos={puntos} alto={320} onElegir={elegirPorMapa} /></div>

      <div className="rejilla">
        {visibles.map((d) => (
          <button key={d.id} className="boleto" onClick={() => abrir(d)}>
            <div className={'cab ' + claseCat(d.categoria)}><small>{d.region} · {d.categoria}</small><b>{d.nombre}</b></div>
            <div className="cuerpo">
              <p>{d.descripcion}</p>
              <div className="fila"><span className="precio">Q{d.costo_diario_gtq}/día</span><span className="suave peq">aprox. por persona</span></div>
            </div>
          </button>
        ))}
      </div>

      {abierto && (
        <Modal titulo={abierto.nombre} onCerrar={() => setAbierto(null)}>
          <div className="fila" style={{ marginBottom: 10 }}>
            <span className="etiqueta jade">{abierto.categoria}</span><span className="etiqueta">{abierto.departamento}</span><span className="etiqueta">{abierto.region}</span>
          </div>
          <p>{abierto.descripcion}</p>
          <p className="suave peq">Gasto diario aproximado: <b>Q{abierto.costo_diario_gtq}</b> por persona · Mejor época: {abierto.mejor_epoca || 'todo el año'}</p>
          <div className="dos-col">
            <div>
              <h3>Actividades</h3>
              {actividades.filter((a) => a.destino_id === abierto.id).map((a) => (
                <p key={a.id} style={{ marginBottom: 6 }}>{a.nombre}<br /><span className="suave peq">{a.duracion_horas} h · {a.costo_gtq ? 'Q' + a.costo_gtq : 'Gratis'}</span></p>
              ))}
              {!actividades.some((a) => a.destino_id === abierto.id) && <p className="suave peq">Sin actividades registradas.</p>}
            </div>
            <div>
              <h3>Para probar en {abierto.departamento}</h3>
              {platillos.filter((p) => p.departamento_origen === abierto.departamento).map((p) => <p key={p.id} style={{ marginBottom: 6 }}>{p.nombre}<br /><span className="suave peq">{p.tipo}</span></p>)}
              {!platillos.some((p) => p.departamento_origen === abierto.departamento) && <p className="suave peq">Sin platillos locales registrados; mira la comida nacional en la Guía Chapín.</p>}
            </div>
          </div>
          <div className="fila" style={{ marginTop: 16 }}>
            <button className="btn" onClick={() => navegar(`/planificador?q=${encodeURIComponent(`Quiero planificar un viaje a ${abierto.nombre} de 2 días para 2 personas`)}`)}>Planificar un viaje aquí</button>
            <button className="btn sec" onClick={() => navegar('/chat')}>Preguntar a la Guía</button>
          </div>
        </Modal>
      )}
    </>
  );
}
