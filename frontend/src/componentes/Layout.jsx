import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';

// Enlace del menú. "end" hace que Inicio solo se marque en "/"
const Enlace = ({ to, end, children }) => (
  <NavLink to={to} end={end} className={({ isActive }) => 'enlace' + (isActive ? ' activo' : '')}>{children}</NavLink>
);

export default function Layout() {
  const { user, salir } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const [oscuro, setOscuro] = useState(document.documentElement.dataset.theme === 'dark');
  const ubicacion = useLocation();

  useEffect(() => setAbierto(false), [ubicacion.pathname]); // cierra el menú móvil al navegar

  const cambiarTema = () => {
    const nuevo = oscuro ? 'light' : 'dark';
    document.documentElement.dataset.theme = nuevo;
    try { localStorage.setItem('rc_tema', nuevo); } catch { /* sin almacenamiento */ }
    setOscuro(!oscuro);
  };

  const pct = user.limite_tokens > 0 ? Math.min(100, Math.round((user.tokens_usados / user.limite_tokens) * 100)) : 100;
  const claseMedidor = pct >= 100 ? 'lleno' : pct >= 80 ? 'alto' : '';

  return (
    <div className="app">
      <div className="barra-movil">
        <button onClick={() => setAbierto(true)} aria-label="Abrir menú">☰</button>
        <b style={{ fontFamily: 'Fraunces, Georgia, serif' }}>Ruta Chapina</b>
      </div>

      <aside className={'menu' + (abierto ? ' abierto' : '')}>
        <div className="marca"><b>Ruta Chapina</b><span>Pasaporte de Guatemala</span></div>
        <div className="tejido" />
        <nav>
          <Enlace to="/" end>Inicio</Enlace>
          <div className="grupo">Servicios de IA</div>
          <Enlace to="/chat">Guía Chapín (chat)</Enlace>
          <Enlace to="/planificador">Planificador de ruta</Enlace>
          <Enlace to="/ajuste">Ajuste de plan</Enlace>
          <div className="grupo">Explorar</div>
          <Enlace to="/explorar">Destinos y sabores</Enlace>
          <div className="grupo">Mi cuenta</div>
          <Enlace to="/historial">Historial</Enlace>
          <Enlace to="/consumo">{user.rol === 'admin' ? 'Consumo de tokens' : 'Mi consumo'}</Enlace>
          {user.rol === 'admin' && (
            <>
              <div className="grupo">Administración</div>
              <Enlace to="/admin/usuarios">Usuarios</Enlace>
              <Enlace to="/admin/servicios">Servicios de IA</Enlace>
              <Enlace to="/admin/catalogo">Catálogo y datos</Enlace>
            </>
          )}
        </nav>

        <div className="pie">
          <div className="peq"><b>{user.nombre}</b> · {user.rol === 'admin' ? 'Administrador' : 'Usuario'}</div>
          <div className={'medidor ' + claseMedidor}><i style={{ width: pct + '%' }} /></div>
          <div className="peq suave">{user.tokens_usados.toLocaleString('es-GT')} / {user.limite_tokens.toLocaleString('es-GT')} tokens</div>
          <div className="fila" style={{ marginTop: 10 }}>
            <button className="btn sec mini" onClick={cambiarTema}>{oscuro ? 'Modo claro' : 'Modo oscuro'}</button>
            <button className="btn sec mini" onClick={salir}>Cerrar sesión</button>
          </div>
        </div>
      </aside>

      <main className="contenido"><div className="pagina"><Outlet /></div></main>
    </div>
  );
}
