import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, getToken, onSesionExpirada, setToken } from './api';

// Contexto: guarda quién tiene la sesión iniciada y lo comparte con toda la app
const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [cargando, setCargando] = useState(!!getToken()); // si hay token guardado, primero lo validamos

  const cerrarLocal = useCallback(() => { setToken(null); setUser(null); }, []);
  useEffect(() => { onSesionExpirada(cerrarLocal); }, [cerrarLocal]);

  // Pide los datos del usuario (incluye tokens usados y su límite)
  const refrescar = useCallback(async () => {
    const u = await api('/auth/yo');
    setUser(u);
    return u;
  }, []);

  useEffect(() => {
    if (!getToken()) return;
    refrescar().catch(cerrarLocal).finally(() => setCargando(false));
  }, [refrescar, cerrarLocal]);

  const entrar = async (email, password) => {
    const r = await api('/auth/login', { method: 'POST', form: { username: email.trim(), password } });
    setToken(r.access_token);
    await refrescar();
  };

  const salir = async () => {
    try { await api('/auth/logout', { method: 'POST' }); } catch { /* da igual si falla */ }
    cerrarLocal();
  };

  return <Ctx.Provider value={{ user, cargando, entrar, salir, refrescar }}>{children}</Ctx.Provider>;
}
