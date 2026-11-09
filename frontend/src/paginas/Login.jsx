import { useState } from 'react';
import { useAuth } from '../auth';
import Emblema from '../componentes/Emblema';

export default function Login() {
  const { entrar } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  const enviar = async (e) => {
    e.preventDefault();
    setError(''); setEnviando(true);
    try { await entrar(email, password); }
    catch (err) { setError(err.message); }
    finally { setEnviando(false); }
  };

  return (
    <div className="login">
      <div className="lado">
        <div className="pasaporte">
          <Emblema />
          <div className="dato">Guatemala · Centroamérica</div>
          <h1 style={{ fontSize: '2.4rem' }}>Ruta Chapina</h1>
          <div className="dato">Pasaporte de turismo y sabores</div>
          <div className="tejido" style={{ width: '70%', marginTop: 22, borderRadius: 4 }} />
        </div>
      </div>
      <form className="form" onSubmit={enviar}>
        <h1>Bienvenido, viajero</h1>
        <p className="suave">Inicia sesión para planificar tu próxima aventura por Guatemala.</p>
        {error && <div className="error" role="alert">{error}</div>}
        <div className="campo">
          <label htmlFor="email">Correo electrónico</label>
          <input id="email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="campo">
          <label htmlFor="pw">Contraseña</label>
          <input id="pw" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <button className="btn" disabled={enviando}>{enviando ? 'Entrando…' : 'Entrar'}</button>
      </form>
    </div>
  );
}
