import { useEffect, useState } from 'react'
import { api, mensajeError } from '../api'

export default function Administracion() {
  const [usuarios, setUsuarios] = useState([])
  const [logs, setLogs] = useState([])
  const [filtro, setFiltro] = useState('')
  const [accion, setAccion] = useState('')
  const [fecha, setFecha] = useState('')
  const [nuevo, setNuevo] = useState({ usuario: '', email: '', contrasena: '', rol: 'Corredor' })
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  async function cargarUsuarios() {
    try { const res = await api.get('/usuarios/'); setUsuarios(res.data) }
    catch (e) { setError(mensajeError(e)) }
  }
  async function cargarLogs() {
    try { const res = await api.get('/auditoria/', { params: { usuario: filtro, accion, fecha } }); setLogs(res.data) }
    catch (e) { setError(mensajeError(e)) }
  }
  useEffect(() => { cargarUsuarios(); cargarLogs() }, [])

  async function crear(e) {
    e.preventDefault(); setError(''); setMensaje('')
    try {
      await api.post('/usuarios/', nuevo)
      setMensaje('Usuario creado. Configurará MFA al iniciar sesión.')
      setNuevo({ usuario: '', email: '', contrasena: '', rol: 'Corredor' })
      await cargarUsuarios(); await cargarLogs()
    } catch (e) { setError(mensajeError(e)) }
  }
  async function cambiarRol(u, rol) {
    if (!window.confirm(`¿Cambiar el rol de ${u.usuario} a ${rol}?`)) return
    try { await api.patch(`/usuarios/${u.id}/`, { rol }); await cargarUsuarios(); await cargarLogs() }
    catch (e) { setError(mensajeError(e)) }
  }
  async function cambiarActivo(u) {
    if (!window.confirm(`¿${u.activo ? 'Desactivar' : 'Activar'} la cuenta ${u.usuario}?`)) return
    try { await api.patch(`/usuarios/${u.id}/`, { activo: !u.activo }); await cargarUsuarios(); await cargarLogs() }
    catch (e) { setError(mensajeError(e)) }
  }

  return <div>
    <h1>Administración y auditoría</h1>
    <p className="suave">Solo el rol Administrador puede ingresar a estas secciones.</p>
    {error && <div className="alerta error" role="alert">{error}</div>}
    {mensaje && <div className="alerta exito">{mensaje}</div>}
    <div className="columnas">
      <section className="tarjeta">
        <h2>Crear usuario</h2><form onSubmit={crear} className="formulario">
          <label>Usuario<input required value={nuevo.usuario} onChange={e => setNuevo({ ...nuevo, usuario: e.target.value })} /></label>
          <label>Correo<input type="email" value={nuevo.email} onChange={e => setNuevo({ ...nuevo, email: e.target.value })} /></label>
          <label>Contraseña temporal<input required type="password" minLength="10" value={nuevo.contrasena}
            onChange={e => setNuevo({ ...nuevo, contrasena: e.target.value })} /></label>
          <label>Rol<select value={nuevo.rol} onChange={e => setNuevo({ ...nuevo, rol: e.target.value })}>
            <option>Corredor</option><option>Administrador</option></select></label>
          <button className="boton">Crear usuario</button>
        </form>
      </section>
      <section className="tarjeta"><h2>Usuarios y permisos</h2>
        <div className="tabla-scroll"><table><thead><tr><th>Usuario</th><th>Rol</th><th>Estado</th><th>Acción</th></tr></thead>
          <tbody>{usuarios.map(u => <tr key={u.id}><td>{u.usuario}</td><td>
            <select value={u.rol} onChange={e => cambiarRol(u, e.target.value)}>
              <option>Corredor</option><option>Administrador</option><option disabled>Sin rol</option>
            </select></td><td>{u.activo ? 'Activo' : 'Desactivado'}</td><td>
              <button className="boton pequeno secundario" onClick={() => cambiarActivo(u)}>
                {u.activo ? 'Desactivar' : 'Activar'}</button></td></tr>)}</tbody></table></div>
      </section>
    </div>
    <section className="tarjeta"><h2>Auditoría (solo lectura)</h2>
      <div className="filtros"><label>Usuario<input value={filtro} onChange={e => setFiltro(e.target.value)} placeholder="Nombre" /></label>
        <label>Acción<input value={accion} onChange={e => setAccion(e.target.value)} placeholder="CREAR, EDITAR, LOGIN..." /></label>
        <label>Fecha<input type="date" value={fecha} onChange={e => setFecha(e.target.value)} /></label>
        <button className="boton" onClick={cargarLogs}>Filtrar</button></div>
      <div className="tabla-scroll"><table><thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Detalle</th></tr></thead>
        <tbody>{logs.map(log => <tr key={log.id}><td>{new Date(log.fecha).toLocaleString('es-CL')}</td>
          <td>{log.usuario}</td><td>{log.accion}</td><td>{log.detalle}</td></tr>)}</tbody></table></div>
      {!logs.length && <p className="suave">No se encontraron eventos para los filtros.</p>}
    </section>
  </div>
}