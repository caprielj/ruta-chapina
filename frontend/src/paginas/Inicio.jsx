import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import Emblema from '../componentes/Emblema';
import Sellos from '../componentes/Sellos';
import { leerSellos } from '../sellos';

// Los tres servicios de IA, presentados como boletos de viaje
const SERVICIOS = [
  { to: '/chat', clase: 'cat-naturaleza', sub: 'Chatbot con RAG', titulo: 'Guía Chapín', texto: 'Pregunta por destinos, actividades y platillos. Responde con datos de la base y cita sus fuentes.' },
  { to: '/planificador', clase: 'cat-cultural', sub: 'Agente', titulo: 'Planificador de ruta', texto: 'Cuéntale tus intereses y presupuesto: busca destinos, consulta clima y distancias y arma tu itinerario.' },
  { to: '/ajuste', clase: 'cat-aventura', sub: 'Agente', titulo: 'Ajuste de plan', texto: '¿Llueve o cambió el presupuesto? Busca alternativas y reordena tu plan.' },
];

export default function Inicio() {
  const { user } = useAuth();
  const sellos = leerSellos(user.id);

  return (
    <>
      <div className="encabezado">
        <h1>¡Qué gusto verte, {user.nombre.split(' ')[0]}!</h1>
        <p>¿A dónde nos llevan los volcanes hoy?</p>
      </div>

      <div className="rejilla dos" style={{ marginBottom: 22 }}>
        <div className="pasaporte">
          <Emblema />
          <div className="dato">Titular</div><div className="valor">{user.nombre}</div>
          <div className="dato">Categoría</div><div className="valor">{user.rol === 'admin' ? 'Administrador' : 'Viajero'}</div>
          <div className="dato">Tokens disponibles</div>
          <div className="valor">{Math.max(user.limite_tokens - user.tokens_usados, 0).toLocaleString('es-GT')}</div>
          <div className="dato">Destinos sellados</div><div className="valor">{sellos.length}</div>
        </div>
        <div className="tarjeta" style={{ margin: 0 }}>
          <h2>Tus sellos</h2>
          <Sellos sellos={sellos} />
        </div>
      </div>

      <h2>Servicios de IA</h2>
      <div className="rejilla" style={{ marginBottom: 22 }}>
        {SERVICIOS.map((s) => (
          <Link key={s.to} to={s.to} className="boleto">
            <div className={'cab ' + s.clase}><small>{s.sub}</small><b>{s.titulo}</b></div>
            <div className="cuerpo"><p style={{ WebkitLineClamp: 5 }}>{s.texto}</p></div>
          </Link>
        ))}
      </div>
    </>
  );
}
