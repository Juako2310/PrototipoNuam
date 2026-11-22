import { useEffect, useState } from 'react'
import { api, mensajeError } from '../api'

const vacio = { rut: '', anio: '', monto: '', factor: '1.000000' }

export default function Mantenedor({ administrador }) {
  const [registros, setRegistros] = useState([])
  const [rutFiltro, setRutFiltro] = useState('')
  const [anioFiltro, setAnioFiltro] = useState('')
  const [formulario, setFormulario] = useState(vacio)
  const [editando, setEditando] = useState(null)
  const [bajas, setBajas] = useState([])
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  async function cargar() {
    try {
      const resultado = await api.get('/calificaciones/', { params: { rut: rutFiltro, anio: anioFiltro } })
      setRegistros(resultado.data)
      setError('')
    } catch (e) { setError(mensajeError(e)) }
  }
  useEffect(() => { cargar() }, [])

  function cambiar(campo, valor) { setFormulario({ ...formulario, [campo]: valor }) }
  function cancelar() { setEditando(null); setFormulario(vacio) }

  async function guardar(e) {
    e.preventDefault(); setMensaje(''); setError('')
    if (editando !== null && !window.confirm('¿Confirmas que deseas modificar esta calificación?')) return
    try {
      if (editando !== null) await api.put(`/calificaciones/${editando}/`, formulario)
      else await api.post('/calificaciones/', formulario)
      setMensaje(editando !== null ? 'Registro actualizado y auditado.' : 'Registro creado correctamente.')
      cancelar(); await cargar()
    } catch (e) { setError(mensajeError(e)) }
  }

  function comenzarEdicion(c) {
    setEditando(c.id)
    setFormulario({ rut: c.rut, anio: String(c.anio), monto: String(c.monto), factor: String(c.factor) })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function darBaja(c) {
    if (!window.confirm(`¿Confirmas dar de baja ${c.rut} del año ${c.anio}?\nLa acción queda auditada.`)) return
    try { await api.delete(`/calificaciones/${c.id}/`); setMensaje('Registro dado de baja.'); await cargar() }
    catch (e) { setError(mensajeError(e)) }
  }

  async function verBajas() {
    try { const res = await api.get('/calificaciones/bajas/'); setBajas(res.data) }
    catch (e) { setError(mensajeError(e)) }
  }
  async function restaurar(c) {
    if (!window.confirm(`¿Restaurar ${c.rut} del año ${c.anio}?`)) return
    try { await api.post(`/calificaciones/${c.id}/restaurar/`); await verBajas(); await cargar(); setMensaje('Registro restaurado.') }
    catch (e) { setError(mensajeError(e)) }
  }

  return <div>
    <h1>Calificaciones tributarias</h1>
    <p className="suave">Busca y administra registros de períodos abiertos. Los años cerrados están en el historial.</p>
    {error && <div className="alerta error" role="alert">{error}</div>}
    {mensaje && <div className="alerta exito">{mensaje}</div>}
    <div className="columnas">
      <section className="tarjeta">
        <h2>{editando !== null ? 'Editar calificación' : 'Nueva calificación'}</h2>
        <form onSubmit={guardar} className="formulario">
          <label>RUT del emisor<input required placeholder="76.123.456-7" value={formulario.rut}
            onChange={e => cambiar('rut', e.target.value)} /></label>
          <label>Año tributario<input type="number" min="2000" max="2100" required value={formulario.anio}
            onChange={e => cambiar('anio', e.target.value)} /></label>
          <label>Monto<input type="number" min="0.01" step="0.01" required value={formulario.monto}
            onChange={e => cambiar('monto', e.target.value)} /></label>
          <label>Factor<input type="number" min="0.000001" step="0.000001" required value={formulario.factor}
            onChange={e => cambiar('factor', e.target.value)} /></label>
          <button type="submit" className="boton">{editando !== null ? 'Guardar cambios' : 'Crear registro'}</button>
          {editando !== null && <button type="button" className="boton secundario" onClick={cancelar}>Cancelar</button>}
        </form>
      </section>
      <section className="tarjeta">
        <h2>Registros centralizados</h2>
        <div className="filtros">
          <label>Buscar por RUT<input value={rutFiltro} onChange={e => setRutFiltro(e.target.value)}
            placeholder="Parte del RUT" /></label>
          <label>Año<input type="number" value={anioFiltro} onChange={e => setAnioFiltro(e.target.value)}
            placeholder="Ej. 2026" /></label>
          <button className="boton" onClick={cargar}>Buscar</button>
          <button className="boton secundario" onClick={() => { setRutFiltro(''); setAnioFiltro('') }}>
            Limpiar filtros</button>
        </div>
        <div className="tabla-scroll"><table>
          <thead><tr><th>RUT</th><th>Año</th><th>Monto</th><th>Factor</th><th>Acciones</th></tr></thead>
          <tbody>{registros.map(c => <tr key={c.id}>
            <td>{c.rut}</td><td>{c.anio}</td><td>${Number(c.monto).toLocaleString('es-CL')}</td>
            <td>{c.factor}</td><td><div className="acciones">
              <button className="boton pequeno secundario" onClick={() => comenzarEdicion(c)}>Editar</button>
              {administrador && <button className="boton pequeno peligro" onClick={() => darBaja(c)}>Dar de baja</button>}
            </div></td>
          </tr>)}</tbody></table></div>
        {registros.length === 0 && <p className="suave">Sin registros para los filtros actuales.</p>}
      </section>
    </div>
    {administrador && <section className="tarjeta">
      <h2>Registros dados de baja</h2><button className="boton secundario" onClick={verBajas}>Consultar bajas</button>
      {bajas.map(c => <p key={c.id}>{c.rut} / {c.anio} — {c.estado} {' '}
        <button className="boton pequeno" onClick={() => restaurar(c)}>Restaurar</button></p>)}
    </section>}
  </div>
}