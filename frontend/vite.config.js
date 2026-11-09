import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Configuración de Vite: solo activa el plugin de React
export default defineConfig({
  plugins: [react()],
});
