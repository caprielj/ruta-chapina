// Sellos del pasaporte: un círculo por cada destino consultado
const COLORES = ['#b3262e', '#1d6b57', '#a4521c', '#6a4b86', '#1c6f8f'];

export default function Sellos({ sellos }) {
  if (!sellos.length) {
    return <p className="suave">Aún no tienes sellos. Pregunta por un destino en la Guía Chapín o ábrelo en Explorar y se sellará aquí.</p>;
  }
  return (
    <div className="sellos">
      {sellos.map((s) => (
        <div key={s.id} className="sello" style={{ color: COLORES[s.id % COLORES.length], transform: `rotate(${((s.id * 37) % 15) - 7}deg)` }}>
          <div>{s.nombre}<small>{s.fecha}</small></div>
        </div>
      ))}
    </div>
  );
}
