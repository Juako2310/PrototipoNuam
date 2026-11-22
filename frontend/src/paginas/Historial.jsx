import { useEffect, useState } from 'react'
import { api, mensajeError } from '../api'

export default function Historial({ administrador }) {
  const [periodos, setPeriodos] = useState([])
  const [anio, setAnio] = useState('')
  const [nuevoCierre, setNuevoCierre] = useState('')
  const [registros, setRegistros] = useState([])
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  async function cargarPeriodos() {
    try {
      const res = await api.get('/periodos/')
      setPeriodos(res.data)
    } catch (e) { setError(mensajeError(e)) }
  }
  useEffect(() => { cargarPeriodos() }, [])

  async function consultar() {
    if (!anio) return setError('Selecciona un año cerrado.')
    try {
      const res = await api.get('/historial/', { params: { anio } })
      setRegistros(res.data); setError('')
    } catch (e) { setError(mensajeError(e)) }
  }
  async function cerrar() {
    if (!nuevoCierre) return setError('Escribe un año.')
    if (!window.confirm(`¿Cerrar DEFINITIVAMENTE el año ${nuevoCierre}?\nLos registros no podrán editarse.`)) return
    try {
      const res = await api.post('/periodos/cerrar/', { anio: nuevoCierre })
      setMensaje(res.data.mensaje); setError(''); await cargarPeriodos()
    } catch (e) { setError(mensajeError(e)) }
  }
  async function exportar(formato) {
    if (!anio) return
    try {
      const res = await api.get('/historial/exportar/', { params: { anio, formato }, responseType: 'blob' })
      const enlace = document.createElement('a')
      const url = URL.createObjectURL(res.data)
      enlace.href = url
      enlace.download = `historial_nuam_${anio}.${formato}`
      enlace.click()
      URL.revokeObjectURL(url)
    } catch (e) { setError(mensajeError(e)) }
  }
  return <div>
    <h1>Historial tributario anual</h1>
    <p className="suave">Consulta períodos cerrados. No es posible editarlos, eliminarlos ni importar registros adicionales.</p>
    {error && <div className="alerta error" role="alert">{error}</div>}
    {mensaje && <div className="alerta exito">{mensaje}</div>}
    <section className="tarjeta">
      <h2>Consultar y exportar historial</h2>
      <div className="filtros"><label>Año cerrado<select value={anio} onChange={e => { setAnio(e.target.value); setRegistros([]) }}>
        <option value="">Selecciona un año</option>
        {periodos.filter(p => p.cerrado).map(p => <option key={p.anio} value={p.anio}>{p.anio}</option>)}
      </select></label>
        <button className="boton" onClick={consultar}>Consultar</button>
        <button className="boton secundario" onClick={() => exportar('csv')} disabled={!anio}>Exportar CSV</button>
        <button className="boton secundario" onClick={() => exportar('xlsx')} disabled={!anio}>Exportar Excel</button></div>
      <div className="tabla-scroll"><table><thead><tr><th>RUT</th><th>Año</th><th>Monto</th><th>Factor</th><th>Estado</th></tr></thead>
        <tbody>{registros.map(r => <tr key={r.id}><td>{r.rut}</td><td>{r.anio}</td>
          <td>{r.monto}</td><td>{r.factor}</td><td>{r.estado}</td></tr>)}</tbody></table></div>
      {!registros.length && <p className="suave">Selecciona un año cerrado y presiona Consultar.</p>}
    </section>
    {administrador && <section className="tarjeta">
      <h2>Cerrar período (solo administrador)</h2>
      <p>Para la demostración, crea primero algunas calificaciones de un año y después ciérralo.
        Esta acción es irreversible desde la interfaz.</p>
      <div className="filtros"><label>Año<input type="number" min="2000" max="2100" value={nuevoCierre}
        onChange={e => setNuevoCierre(e.target.value)} /></label>
        <button className="boton peligro" onClick={cerrar}>Cerrar período</button></div>
      <p className="suave">Años existentes: {periodos.map(p => `${p.anio} (${p.cerrado ? 'cerrado' : 'abierto'})`).join(', ') || 'sin datos'}</p>
    </section>}
  </div>
}