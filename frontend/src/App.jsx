import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth';
import Layout from './componentes/Layout';
import Login from './paginas/Login';
import Inicio from './paginas/Inicio';
import Chat from './paginas/Chat';
import Agente from './paginas/Agente';
import Resultado from './paginas/Resultado';
import Historial from './paginas/Historial';
import Consumo from './paginas/Consumo';
import Explorar from './paginas/Explorar';
import Usuarios from './paginas/admin/Usuarios';
import Servicios from './paginas/admin/Servicios';
import Catalogo from './paginas/admin/Catalogo';

// Protege las pantallas de administración: un usuario normal vuelve al inicio
function SoloAdmin({ children }) {
  const { user } = useAuth();
  return user.rol === 'admin' ? children : <Navigate to="/" replace />;
}

function Rutas() {
  const { user, cargando } = useAuth();
  if (cargando) return <p className="centro suave" style={{ marginTop: '30vh' }}>Cargando…</p>;
  if (!user) return <Routes><Route path="*" element={<Login />} /></Routes>; // sin sesión: solo el login

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Inicio />} />
        <Route path="chat" element={<Chat />} />
        <Route path="planificador" element={<Agente tipo="planificador" />} />
        <Route path="ajuste" element={<Agente tipo="ajuste" />} />
        <Route path="resultado/:id" element={<Resultado />} />
        <Route path="explorar" element={<Explorar />} />
        <Route path="historial" element={<Historial />} />
        <Route path="consumo" element={<Consumo />} />
        <Route path="admin/usuarios" element={<SoloAdmin><Usuarios /></SoloAdmin>} />
        <Route path="admin/servicios" element={<SoloAdmin><Servicios /></SoloAdmin>} />
        <Route path="admin/catalogo" element={<SoloAdmin><Catalogo /></SoloAdmin>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider><Rutas /></AuthProvider>
    </BrowserRouter>
  );
}
