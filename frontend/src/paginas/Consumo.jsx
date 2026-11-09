import { useCallback, useEffect, useMemo, useState } from 'react';
import { api, descargar } from '../api';
import { useAuth } from '../auth';

const hoy = () => new Date().toLocaleDateString('en-CA'); // AAAA-MM-DD en hora local
const haceDias = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return d.toLocaleDateString('en-CA'); };
const num = (n) => Number(n || 0).toLocaleString('es-GT');
const fh = (s) => (s || '').slice(0, 16).replace('T', ' ');

/**
 * Reporte web de consultas y consumo acumulado por servicio.
 * Usa los mismos endpoints (/consumo/...) que el reporte de Power BI, por eso las cifras coinciden.
 */
export default function Consumo() {
  const { user } = useAuth();
  const esAdmin = user.rol === 'admin';
  const [servicios, setServicios] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [f, setF] = useState({ usuario_id: '', servicio_id: '', desde: '', hasta: '' });
  const [porServicio, setPorServicio] = useState([]);
  const [porDia, setPorDia] = useState([]);
  const [detalle, setDetalle] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api('/servicios').then(setServicios).catch(() => {});
    if (esAdmin) api('/usuarios').then(setUsuarios).catch(() => {});
  }, [esAdmin]);

  const cargar = useCallback(async () => {
    setError('');
    try {
      const p = { usuario_id: f.usuario_id, servicio_id: f.servicio_id, desde: f.desde, hasta: f.hasta };
      const [a, b, c, r] = await Promise.all([
        api('/consumo/por-servicio', { params: p }),
        api('/consumo/por-dia', { params: p }),
        api('/consumo/detalle', { params: { ...p, limite: 1000 } }),
        api('/consumo/resumen'),
      ]);
      setPorServicio(a); setPorDia(b); setDetalle(c); setResumen(r);
    } catch (e) { setError(e.message); }
  }, [f]);
  useEffect(() => { cargar(); }, [cargar]);

  const total = useMemo(() => porServicio.reduce((t, s) => ({
    consultas: t.consultas + s.consultas, entrada: t.entrada + s.tokens_entrada, salida: t.salida + s.tokens_salida, tokens: t.tokens + s.tokens_total,
  }), { consultas: 0, entrada: 0, salida: 0, tokens: 0 }), [porServicio]);

  const maxServ = Math.max(1, ...porServicio.map((s) => s.tokens_total));
  const maxDia = Math.max(1, ...porDia.map((d) => d.tokens_total));
  const cambiar = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const exportar = () => {
    const cab = 'id,fecha_hora,usuario,servicio,tokens_entrada,tokens_salida,tokens_total';
    const filas = detalle.map((d) => [d.id, fh(d.fecha_hora), `"${d.usuario}"`, `"${d.servicio}"`, d.tokens_entrada, d.tokens_salida, d.tokens_total].join(','));
    descargar('consumo.csv', [cab, ...filas].join('\n'));
  };

  return (
    <>
      <div className="encabezado">
        <h1>{esAdmin ? 'Consumo de tokens' : 'Mi consumo'}</h1>
        <p>{esAdmin ? 'Uso general de la plataforma, con filtros por usuario, servicio y fecha.' : 'Tus consultas realizadas y los tokens que has consumido.'}</p>
      </div>

      {resumen && (
        <div className="tarjeta">
          <div className="fila"><b>Mi límite de tokens</b><div className="sep" /><span className="suave">{num(resumen.tokens_usados)} de {num(resumen.limite_tokens)} · quedan {num(resumen.tokens_restantes)}</span></div>
          <div className={'medidor ' + (resumen.tokens_restantes === 0 ? 'lleno' : resumen.tokens_usados / Math.max(resumen.limite_tokens, 1) >= 0.8 ? 'alto' : '')}>
            <i style={{ width: Math.min(100, (resumen.tokens_usados / Math.max(resumen.limite_tokens, 1)) * 100) + '%' }} />
          </div>
        </div>
      )}

      <div className="filtros">
        {esAdmin && <label>Usuario<select value={f.usuario_id} onChange={cambiar('usuario_id')}><option value="">Todos</option>{usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}</select></label>}
        <label>Servicio<select value={f.servicio_id} onChange={cambiar('servicio_id')}><option value="">Todos</option>{servicios.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}</select></label>
        <label>Desde<input type="date" value={f.desde} onChange={cambiar('desde')} /></label>
        <label>Hasta<input type="date" value={f.hasta} onChange={cambiar('hasta')} /></label>
        <button className="btn sec mini" onClick={() => setF({ ...f, desde: hoy(), hasta: hoy() })}>Hoy</button>
        <button className="btn sec mini" onClick={() => setF({ ...f, desde: haceDias(6), hasta: hoy() })}>7 días</button>
        <button className="btn sec mini" onClick={() => setF({ ...f, desde: '', hasta: '' })}>Todo</button>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="kpis">
        <div className="kpi"><small>Consultas</small><b>{num(total.consultas)}</b></div>
        <div className="kpi"><small>Tokens totales</small><b>{num(total.tokens)}</b></div>
        <div className="kpi"><small>Tokens de entrada</small><b>{num(total.entrada)}</b></div>
        <div className="kpi"><small>Tokens de salida</small><b>{num(total.salida)}</b></div>
      </div>

      <div className="rejilla dos">
        <div className="tarjeta">
          <h2>Consumo acumulado por servicio</h2>
          {porServicio.map((s) => (
            <div className="barra-h" key={s.servicio_id}>
              <span>{s.servicio}</span>
              <div className="pista"><i style={{ width: (s.tokens_total / maxServ) * 100 + '%' }} /></div>
              <span className="num">{num(s.tokens_total)} · {s.consultas} consulta(s)</span>
            </div>
          ))}
        </div>
        <div className="tarjeta">
          <h2>Tokens por día</h2>
          {porDia.length === 0 ? <p className="suave">Sin consultas en este periodo.</p> : (
            <div className="columnas">
              {porDia.map((d) => (
                <div className="columna" key={d.fecha} title={`${d.fecha}: ${num(d.tokens_total)} tokens, ${d.consultas} consulta(s)`}>
                  <i style={{ height: Math.max(2, (d.tokens_total / maxDia) * 100) + '%' }} />
                  <small>{d.fecha.slice(5)}</small>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="fila" style={{ margin: '8px 0 10px' }}>
        <h2 style={{ margin: 0 }}>Detalle de consultas</h2><div className="sep" />
        <button className="btn sec mini" onClick={exportar} disabled={!detalle.length}>Descargar CSV</button>
      </div>
      <div className="tabla-caja">
        <table className="tabla">
          <thead><tr><th>Fecha y hora</th><th>Usuario</th><th>Servicio</th><th className="num">Entrada</th><th className="num">Salida</th><th className="num">Total</th></tr></thead>
          <tbody>
            {detalle.map((d) => (
              <tr key={d.id}><td>{fh(d.fecha_hora)}</td><td>{d.usuario}</td><td>{d.servicio}</td><td className="num">{num(d.tokens_entrada)}</td><td className="num">{num(d.tokens_salida)}</td><td className="num"><b>{num(d.tokens_total)}</b></td></tr>
            ))}
            {detalle.length === 0 && <tr><td colSpan={6} className="suave">No hay consultas con esos filtros.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
