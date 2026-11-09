import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './estilos.css';

// Tema claro u oscuro: recuerda la elección del usuario o usa la del sistema
let tema = 'light';
try {
  tema = localStorage.getItem('rc_tema') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
} catch { /* sin almacenamiento */ }
document.documentElement.dataset.theme = tema;

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>);
