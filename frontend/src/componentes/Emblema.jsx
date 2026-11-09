// Emblema de Ruta Chapina: sol maya (estrella de ocho puntas) sobre un volcán
export default function Emblema({ className = 'emblema' }) {
  return (
    <svg className={className} viewBox="0 0 100 100" role="img" aria-label="Ruta Chapina">
      <circle cx="50" cy="50" r="46" fill="none" stroke="#e9b53a" strokeWidth="2.5" />
      <circle cx="50" cy="50" r="40" fill="none" stroke="#e9b53a" strokeWidth="1" strokeDasharray="2 4" />
      <g fill="#e9b53a">
        <path d="M50 14 55 28 50 24 45 28z" />
        <path d="M50 14 55 28 50 24 45 28z" transform="rotate(45 50 40)" />
        <path d="M50 14 55 28 50 24 45 28z" transform="rotate(-45 50 40)" />
      </g>
      <circle cx="50" cy="38" r="9" fill="#b3262e" />
      <path d="M14 78 38 46l9 12 8-10 31 30z" fill="#e9b53a" />
      <path d="M14 78h72" stroke="#e9b53a" strokeWidth="2.5" />
    </svg>
  );
}
