import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Evita que un nombre con símbolos rompa el HTML del globo emergente
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/**
 * Mapa de Guatemala con OpenStreetMap (gratis, sin clave).
 *  puntos: [{ lat, lon, nombre, sub, n }]
 *   - con "n": pin numerado (parada del itinerario); se unen con una línea según su número
 *   - sin "n": punto pequeño verde (destino cualquiera)
 */
export default function Mapa({ puntos = [], alto = 380, onElegir }) {
  const caja = useRef(null);
  const mapa = useRef(null);
  const capa = useRef(null);

  // Crea el mapa una sola vez
  useEffect(() => {
    const m = L.map(caja.current, { scrollWheelZoom: false }).setView([15.4, -90.4], 7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, attribution: '© OpenStreetMap',
    }).addTo(m);
    capa.current = L.layerGroup().addTo(m);
    mapa.current = m;
    return () => { m.remove(); mapa.current = null; };
  }, []);

  // Redibuja los pines cada vez que cambian los puntos
  useEffect(() => {
    const m = mapa.current;
    if (!m) return;
    capa.current.clearLayers();
    const validos = puntos.filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon));

    validos.forEach((p) => {
      const numerado = p.n != null;
      const icono = L.divIcon({
        className: numerado ? 'pin' : 'pin base',
        html: numerado ? String(p.n) : '',
        iconSize: numerado ? [28, 28] : [14, 14],
        iconAnchor: numerado ? [14, 14] : [7, 7],
      });
      const mk = L.marker([p.lat, p.lon], { icon: icono }).addTo(capa.current);
      mk.bindPopup(`<b>${esc(p.nombre)}</b>${p.sub ? '<br>' + esc(p.sub) : ''}`);
      if (onElegir) mk.on('click', () => onElegir(p));
    });

    const ruta = validos.filter((p) => p.n != null).sort((a, b) => a.n - b.n);
    if (ruta.length > 1) {
      L.polyline(ruta.map((p) => [p.lat, p.lon]), { color: '#b3262e', weight: 3, dashArray: '6 8' }).addTo(capa.current);
    }
    if (validos.length === 1) m.setView([validos[0].lat, validos[0].lon], 10);
    else if (validos.length > 1) m.fitBounds(validos.map((p) => [p.lat, p.lon]), { padding: [30, 30], maxZoom: 11 });
  }, [puntos, onElegir]);

  return <div ref={caja} className="mapa" style={{ height: alto }} />;
}
