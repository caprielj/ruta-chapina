// Cliente HTTP de la API. Todas las páginas hablan con el backend a través de esta función.
const BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const CLAVE = 'rc_token'; // nombre con el que se guarda el token en el navegador

export const getToken = () => localStorage.getItem(CLAVE);
export const setToken = (t) => (t ? localStorage.setItem(CLAVE, t) : localStorage.removeItem(CLAVE));

// El contexto de autenticación registra aquí qué hacer si el servidor responde 401 (sesión vencida)
let alExpirar = () => {};
export const onSesionExpirada = (fn) => { alExpirar = fn; };

// Convierte la respuesta de error de FastAPI en un texto legible
function mensajeError(data, status) {
  const d = data && data.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).slice(1).join('.')}: ${e.msg}`).join(' · ');
  return `Error ${status}`;
}

/**
 * api('/ruta', { method, body, form, params })
 *  - body:   objeto que se envía como JSON
 *  - form:   objeto que se envía como formulario (solo para el login)
 *  - params: parámetros de consulta (?a=1); se ignoran los vacíos
 */
export async function api(ruta, { method = 'GET', body, form, params } = {}) {
  let url = BASE + ruta;
  if (params) {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') q.append(k, v);
    });
    const s = q.toString();
    if (s) url += '?' + s;
  }
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    payload = new URLSearchParams(form).toString();
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let resp;
  try {
    resp = await fetch(url, { method, headers, body: payload });
  } catch {
    throw new Error('No se pudo conectar con el servidor. Si acaba de estar inactivo, espera unos 30 segundos y reintenta.');
  }
  if (resp.status === 204) return null;

  let data = null;
  try { data = await resp.json(); } catch { /* respuesta sin cuerpo JSON */ }

  if (!resp.ok) {
    if (resp.status === 401 && ruta !== '/auth/login') { setToken(null); alExpirar(); }
    throw new Error(mensajeError(data, resp.status));
  }
  return data;
}

// Descarga un texto como archivo (se usa para exportar el consumo a CSV)
export function descargar(nombre, texto, tipo = 'text/csv;charset=utf-8') {
  const url = URL.createObjectURL(new Blob(['﻿' + texto], { type: tipo }));
  const a = document.createElement('a');
  a.href = url; a.download = nombre; a.click();
  URL.revokeObjectURL(url);
}
