import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Muestra texto en Markdown (la IA responde con títulos, listas y tablas).
// react-markdown no ejecuta HTML, así que es seguro mostrar lo que genere el modelo.
export default function Md({ children }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children || ''}</ReactMarkdown>
    </div>
  );
}
