import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import ResultadoAgente from '../componentes/ResultadoAgente';
import { sellar } from '../sellos';

// Configuración de cada agente (la pantalla es la misma, cambian los textos y el endpoint)
const CONFIG = {
  planificador: {
    titulo: 'Planificador de ruta',
    ayuda: 'Cuéntame cuántos días, cuántas personas, tu presupuesto y qué te gusta. El agente busca destinos, consulta el clima real y las distancias, y calcula el presupuesto.',
    ruta: '/agentes/planificador',
    codigo: 'planificador_ruta',
    ejemplos: [
      'Quiero un viaje de 3 días para 2 personas, con Q2500 por persona. Me gustan los volcanes y la gastronomía.',
      'Fin de semana cultural y tranquilo para 1 persona, con Q1500 de presupuesto.',
      'Una aventura de 4 días para 4 amigos con arqueología y naturaleza.',
    ],
  },
  ajuste: {
    titulo: 'Ajuste de plan',
    ayuda: 'Elige un plan que hiciste con el planificador (o descríbelo) y dime qué cambió: lluvia, menos presupuesto, otro interés… El agente busca alternativas y reajusta.',
    ruta: '/agentes/ajuste',
    codigo: 'ajuste_plan',
    ejemplos: [
      'Ahora se pronostica lluvia: cambia las actividades al aire libre por opciones cubiertas o culturales.',
      'El presupuesto bajó a Q1500 por persona; busca alternativas más económicas.',
    ],
  },
};

const FASES = ['Interpretando tu solicitud…', 'Buscando destinos…', 'Consultando clima y distancias…', 'Calculando el presupuesto…', 'Redactando el itinerario…'];

export default function Agente({ tipo }) {
  const cfg = CONFIG[tipo];
  const { user, refrescar } = useAuth();
  const navegar = useNavigate();
  const [params] = useSearchParams();
  const [solicitud, setSolicitud] = useState(params.get('q') || '');
  const [planId, setPlanId] = useState(params.get('plan') || '');
  const [planes, setPlanes] = useState([]);
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [fase, setFase] = useState(0);
  const [error, setError] = useState('');

  // En "Ajuste" cargamos los planes anteriores del planificador para elegir uno
  useEffect(() => {
    if (tipo !== 'ajuste') return;
    (async () => {
      try {
        const servicios = await api('/servicios');
        const plan = servicios.find((s) => s.codigo === 'planificador_ruta');
        if (plan) setPlanes(await api('/agentes/resultados', { params: { servicio_id: plan.id, usuario_id: user.id, limite: 30 } }));
      } catch { /* si falla, el usuario puede describir el plan a mano */ }
    })();
  }, [tipo, user.id]);

  // Mensajes de progreso mientras el agente trabaja (solo informativos)
  useEffect(() => {
    if (!cargando) return;
    setFase(0);
    const t = setInterval(() => setFase((f) => Math.min(f + 1, FASES.length - 1)), 5000);
    return () => clearInterval(t);
  }, [cargando]);

  const ejecutar = async (e) => {
    e.preventDefault();
    setError(''); setResultado(null); setCargando(true);
    try {
      const body = { solicitud: solicitud.trim() };
      if (tipo === 'ajuste' && planId) body.plan_previo_id = Number(planId);
      const r = await api(cfg.ruta, { method: 'POST', body });
      setResultado(r);
      sellar(user.id, r.destinos.map((d) => ({ id: d.id, nombre: d.nombre })));
      refrescar();
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  return (
    <>
      <div className="encabezado"><h1>{cfg.titulo}</h1><p>{cfg.ayuda}</p></div>

      <form className="tarjeta" onSubmit={ejecutar}>
        {tipo === 'ajuste' && (
          <div className="campo">
            <label htmlFor="plan">Plan que quieres ajustar</label>
            <select id="plan" value={planId} onChange={(e) => setPlanId(e.target.value)}>
              <option value="">— Ninguno (lo describo abajo) —</option>
              {planes.map((p) => <option key={p.id} value={p.id}>#{p.id} · {p.creado_en.slice(0, 10)} · {p.solicitud.slice(0, 70)}</option>)}
            </select>
          </div>
        )}
        <div className="campo">
          <label htmlFor="sol">{tipo === 'ajuste' ? '¿Qué cambió?' : '¿Qué viaje quieres hacer?'}</label>
          <textarea id="sol" required minLength={5} maxLength={1500} value={solicitud} onChange={(e) => setSolicitud(e.target.value)} />
        </div>
        <div className="sugerencias" style={{ marginTop: 0 }}>
          {cfg.ejemplos.map((x) => <button type="button" key={x} onClick={() => setSolicitud(x)}>{x.length > 60 ? x.slice(0, 58) + '…' : x}</button>)}
        </div>
        <button className="btn" disabled={cargando || solicitud.trim().length < 5}>{cargando ? 'El agente está trabajando…' : 'Ejecutar agente'}</button>
      </form>

      {error && <div className="error" role="alert">{error}</div>}

      {cargando && (
        <div className="tarjeta estado-trabajando">
          <div className="rueda" />
          <div><b>{FASES[fase]}</b><div className="suave peq">El agente decide qué herramientas usar. Puede tardar hasta un minuto.</div></div>
        </div>
      )}

      {resultado && (
        <>
          <div className="fila" style={{ marginBottom: 14 }}>
            <span className="etiqueta jade">Consumió {resultado.tokens_consulta.toLocaleString('es-GT')} tokens</span>
            <span className="etiqueta">Te quedan {resultado.tokens_restantes.toLocaleString('es-GT')}</span>
            <div className="sep" />
            {tipo === 'planificador' && <button className="btn sec" onClick={() => navegar(`/ajuste?plan=${resultado.resultado_id}`)}>Ajustar este plan</button>}
          </div>
          <ResultadoAgente datos={resultado} />
        </>
      )}
    </>
  );
}
