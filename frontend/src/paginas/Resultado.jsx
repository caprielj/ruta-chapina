import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import ResultadoAgente from '../componentes/ResultadoAgente';

// Muestra un resultado guardado de un agente (se abre desde el historial)
export default function Resultado() {
  const { id } = useParams();
  const [fila, setFila] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api(`/agentes/resultados/${id}`).then(setFila).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="error">{error}</div>;
  if (!fila) return <p className="suave">Cargando…</p>;

  return (
    <>
      <div className="encabezado">
        <p><Link to="/historial">← Volver al historial</Link></p>
        <h1>{fila.servicio}</h1>
        <p>{fila.usuario} · {fila.creado_en.slice(0, 16).replace('T', ' ')}</p>
      </div>
      <div className="tarjeta"><b>Solicitud:</b> {fila.solicitud}</div>
      <ResultadoAgente datos={{ ...fila.resultado, pasos: fila.pasos }} />
    </>
  );
}
