// Sellos del pasaporte: cada destino que el usuario consulta queda "sellado".
// Se guardan en este navegador (localStorage), separados por usuario.
const clave = (uid) => `rc_sellos_${uid}`;

export function leerSellos(uid) {
  try { return JSON.parse(localStorage.getItem(clave(uid)) || '[]'); } catch { return []; }
}

// destinos: [{ id, nombre }]
export function sellar(uid, destinos) {
  if (!uid || !destinos?.length) return;
  const actuales = leerSellos(uid);
  const hoy = new Date().toLocaleDateString('en-CA'); // AAAA-MM-DD
  let cambio = false;
  destinos.forEach((d) => {
    if (d?.id != null && !actuales.some((s) => s.id === d.id)) {
      actuales.push({ id: d.id, nombre: d.nombre, fecha: hoy });
      cambio = true;
    }
  });
  if (cambio) {
    try { localStorage.setItem(clave(uid), JSON.stringify(actuales)); } catch { /* almacenamiento lleno */ }
  }
}
