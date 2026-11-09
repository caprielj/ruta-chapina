import { useCallback, useEffect, useState } from 'react';
import { api } from '../../api';
import { useAuth } from '../../auth';
import Modal from '../../componentes/Modal';

const VACIO = { nombre: '', email: '', password: '', rol: 'usuario', limite_tokens: 100000, activo: true };

export default function Usuarios() {
  const { user } = useAuth();
  const [lista, setLista] = useState([]);
  const [form, setForm] = useState(null); // null = cerrado; objeto = formulario abierto
  const [editandoId, setEditandoId] = useState(null);
  const [error, setError] = useState('');
  const [errorForm, setErrorForm] = useState('');

  const cargar = useCallback(() => api('/usuarios').then(setLista).catch((e) => setError(e.message)), []);
  useEffect(() => { cargar(); }, [cargar]);

  const nuevo = () => { setEditandoId(null); setForm({ ...VACIO }); setErrorForm(''); };
  const editar = (u) => { setEditandoId(u.id); setForm({ nombre: u.nombre, email: u.email, password: '', rol: u.rol, limite_tokens: u.limite_tokens, activo: u.activo }); setErrorForm(''); };

  const guardar = async (e) => {
    e.preventDefault(); setErrorForm('');
    try {
      const body = { ...form, limite_tokens: Number(form.limite_tokens) };
      if (editandoId) {
        if (!body.password) delete body.password; // vacío = no cambiar la contraseña
        await api(`/usuarios/${editandoId}`, { method: 'PUT', body });
      } else {
        delete body.activo; // un usuario nuevo siempre nace activo
        await api('/usuarios', { method: 'POST', body });
      }
      setForm(null); cargar();
    } catch (err) { setErrorForm(err.message); }
  };

  const borrar = async (u) => {
    if (!window.confirm(`¿Eliminar a ${u.nombre}? Se borrarán también sus conversaciones y su consumo.`)) return;
    try { await api(`/usuarios/${u.id}`, { method: 'DELETE' }); cargar(); } catch (err) { setError(err.message); }
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  return (
    <>
      <div className="encabezado fila"><div><h1>Usuarios</h1><p>Crea cuentas, asigna roles y define el límite de tokens de cada usuario.</p></div><div className="sep" /><button className="btn" onClick={nuevo}>Nuevo usuario</button></div>
      {error && <div className="error">{error}</div>}
      <div className="tabla-caja">
        <table className="tabla">
          <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th><th>Tokens (usados / límite)</th><th /></tr></thead>
          <tbody>
            {lista.map((u) => (
              <tr key={u.id}>
                <td>{u.nombre}</td><td>{u.email}</td>
                <td><span className={'etiqueta' + (u.rol === 'admin' ? ' rojo' : '')}>{u.rol}</span></td>
                <td><span className={'etiqueta' + (u.activo ? ' jade' : '')}>{u.activo ? 'activo' : 'inactivo'}</span></td>
                <td>
                  {u.tokens_usados.toLocaleString('es-GT')} / {u.limite_tokens.toLocaleString('es-GT')}
                  <div className={'medidor' + (u.tokens_usados >= u.limite_tokens ? ' lleno' : '')}><i style={{ width: Math.min(100, (u.tokens_usados / Math.max(u.limite_tokens, 1)) * 100) + '%' }} /></div>
                </td>
                <td className="num"><button className="btn sec mini" onClick={() => editar(u)}>Editar</button>{' '}{u.id !== user.id && <button className="btn peligro mini" onClick={() => borrar(u)}>Eliminar</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {form && (
        <Modal titulo={editandoId ? 'Editar usuario' : 'Nuevo usuario'} onCerrar={() => setForm(null)}>
          <form onSubmit={guardar}>
            {errorForm && <div className="error">{errorForm}</div>}
            <div className="campo"><label>Nombre</label><input required minLength={2} value={form.nombre} onChange={set('nombre')} /></div>
            <div className="campo"><label>Correo electrónico</label><input type="email" required value={form.email} onChange={set('email')} /></div>
            <div className="campo"><label>{editandoId ? 'Nueva contraseña (déjala vacía para no cambiarla)' : 'Contraseña (mínimo 8 caracteres)'}</label><input type="password" autoComplete="new-password" minLength={8} maxLength={72} required={!editandoId} value={form.password} onChange={set('password')} /></div>
            <div className="dos-col">
              <div className="campo"><label>Rol</label><select value={form.rol} onChange={set('rol')}><option value="usuario">Usuario</option><option value="admin">Administrador</option></select></div>
              <div className="campo"><label>Límite de tokens</label><input type="number" min={0} required value={form.limite_tokens} onChange={set('limite_tokens')} /></div>
            </div>
            {editandoId && <div className="campo check"><input id="act" type="checkbox" checked={form.activo} onChange={set('activo')} /><label htmlFor="act">Cuenta activa</label></div>}
            <div className="fila"><button className="btn">Guardar</button><button type="button" className="btn sec" onClick={() => setForm(null)}>Cancelar</button></div>
          </form>
        </Modal>
      )}
    </>
  );
}
