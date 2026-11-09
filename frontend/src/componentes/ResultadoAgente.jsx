import { useMemo } from 'react';
import Md from './Md';
import Mapa from './Mapa';

// Nombres amigables de las herramientas que usa el agente
const NOMBRE_PASO = {
  buscar_destinos: 'Buscó destinos',
  detalle_destinos: 'Consultó actividades y platillos',
  consultar_clima: 'Consultó el clima (Open-Meteo)',
  calcular_distancia: 'Calculó distancias (OSRM)',
  calcular_presupuesto: 'Calculó el presupuesto',
};

const fechaCorta = (f) => new Date(f + 'T00:00:00').toLocaleDateString('es-GT', { weekday: 'short', day: 'numeric', month: 'short' });
export const quetzales = (n) => `Q${Number(n || 0).toLocaleString('es-GT')}`;

/**
 * Muestra todo lo que devuelve un agente: pasos, respuesta, clima, mapa con ruta y presupuesto.
 * datos = { respuesta, pasos, destinos, clima, distancias, presupuesto }
 */
export default function ResultadoAgente({ datos }) {
  const { respuesta, pasos = [], destinos = [], clima = [], distancias = [], presupuesto } = datos;

  // Ordena los pines según la cadena de tramos (origen → destino) para dibujar la ruta
  const puntos = useMemo(() => {
    const porNombre = Object.fromEntries(destinos.map((d) => [d.nombre, d]));
    const cadena = distancias.length ? [distancias[0].origen, ...distancias.map((t) => t.destino)] : [];
    const usados = new Set();
    const lista = [];
    cadena.forEach((nombre, i) => {
      const d = porNombre[nombre];
      if (d && !usados.has(nombre)) { usados.add(nombre); lista.push({ ...d, sub: d.departamento, n: lista.length + 1 }); }
    });
    destinos.forEach((d) => { if (!usados.has(d.nombre)) lista.push({ ...d, sub: d.departamento }); });
    return lista;
  }, [destinos, distancias]);

  return (
    <>
      <div className="tarjeta">
        <h2>Cómo lo resolvió el agente</h2>
        {pasos.length === 0 ? (
          <p className="suave">El agente respondió sin usar herramientas.</p>
        ) : (
          <ol className="linea-pasos">
            {pasos.map((p, i) => (
              <li key={i}>
                <span className="num">{i + 1}</span>
                <b>{NOMBRE_PASO[p.herramienta] || p.herramienta}</b>
                <span>{p.resumen}</span>
              </li>
            ))}
          </ol>
        )}
      </div>

      <div className="tarjeta"><Md>{respuesta}</Md></div>

      {puntos.length > 0 && (
        <div className="tarjeta">
          <h2>Mapa</h2>
          <Mapa puntos={puntos} alto={340} />
          {distancias.length > 0 && (
            <div className="tabla-caja" style={{ marginTop: 14 }}>
              <table className="tabla">
                <thead><tr><th>Tramo</th><th className="num">Distancia</th><th className="num">Tiempo</th><th>Fuente</th></tr></thead>
                <tbody>
                  {distancias.map((t, i) => (
                    <tr key={i}><td>{t.origen} → {t.destino}</td><td className="num">{t.km} km</td><td className="num">{t.horas} h</td><td>{t.fuente}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {clima.length > 0 && (
        <div className="tarjeta">
          <h2>Clima</h2>
          {clima.map((c, i) => (
            <div key={i}>
              <b>{c.destino}</b>
              {c.error ? <p className="suave">{c.error}</p> : (
                <div className="dias">
                  {c.dias.map((d) => (
                    <div className="dia" key={d.fecha}>
                      <b>{fechaCorta(d.fecha)}</b>
                      {Math.round(d.min)}° – {Math.round(d.max)}°
                      <div className="lluvia">Lluvia {d.lluvia_pct ?? 0}%</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {presupuesto && (
        <div className="tarjeta">
          <h2>Presupuesto</h2>
          <div className="tabla-caja">
            <table className="tabla">
              <thead><tr><th>Destino</th><th className="num">Días</th><th className="num">Alojamiento y comida</th><th className="num">Actividades</th><th className="num">Subtotal</th></tr></thead>
              <tbody>
                {presupuesto.tramos.map((t, i) => (
                  <tr key={i}>
                    <td>{t.destino}{t.actividades?.length > 0 && <div className="suave peq">{t.actividades.join(', ')}</div>}</td>
                    <td className="num">{t.dias}</td>
                    <td className="num">{quetzales(t.alojamiento_comida_gtq)}</td>
                    <td className="num">{quetzales(t.actividades_gtq)}</td>
                    <td className="num"><b>{quetzales(t.subtotal_gtq)}</b></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="fila" style={{ marginTop: 12 }}>
            <div><div className="suave peq">Total para {presupuesto.personas} persona(s)</div><div className="total-gtq">{quetzales(presupuesto.total_gtq)}</div></div>
            <div><div className="suave peq">Por persona</div><div className="total-gtq">{quetzales(presupuesto.por_persona_gtq)}</div></div>
          </div>
          <p className="suave peq" style={{ margin: '8px 0 0' }}>{presupuesto.nota}</p>
        </div>
      )}
    </>
  );
}
