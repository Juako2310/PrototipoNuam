import { useRef, useState } from 'react'
import { api, mensajeError } from '../api'

export default function Cargas() {
  const [archivo, setArchivo] = useState(null)
  const [vista, setVista] = useState(null)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const input = useRef(null)

  function seleccionar(e) {
    setArchivo(e.target.files?.[0] || null)
    setVista(null); setMensaje(''); setError('')
  }
  function construirFormulario() {
    const datos = new FormData()
    datos.append('file', archivo)
    return datos
  }
  async function previsualizar() {
    if (!archivo) return setError('Primero selecciona un archivo CSV o XLSX.')
    setError(''); setMensaje(''); setOcupado(true)
    try {
      const res = await api.post('/cargas/preview/', construirFormulario())
      setVista(res.data)
      if (!res.data.puede_confirmar) setError('El archivo tiene errores. Corrígelos antes de confirmar.')
    } catch (e) { setError(mensajeError(e)) }
    finally { setOcupado(false) }
  }
  async function confirmar() {
    if (!vista?.puede_confirmar || !archivo) return
    if (!window.confirm(`¿Guardar los ${vista.total} registros del archivo ${archivo.name}?`)) return
    setOcupado(true); setError('')
    try {
      const datos = construirFormulario()
      datos.append('hash_archivo', vista.hash_archivo)
      const res = await api.post('/cargas/confirmar/', datos)
      setMensaje(res.data.mensaje)
      setVista(null); setArchivo(null)
      if (input.current) input.current.value = ''
    } catch (e) {
      setError(mensajeError(e))
      if (e.response?.data?.errores) setVista(v => ({ ...v, errores: e.response.data.errores, puede_confirmar: false }))
    } finally { setOcupado(false) }
  }

  return <div>
    <h1>Carga masiva de calificaciones</h1>
    <p className="suave">Primero revisa los errores y la vista previa. Nada se guarda hasta presionar "Confirmar carga".</p>
    <section className="tarjeta">
      <h2>Selecciona una planilla</h2>
      <p>Formatos admitidos: <b>.csv o .xlsx</b>. Columnas: <code>rut, anio, monto, factor</code>
        (el factor es opcional). Máximo 2 MB y 1000 filas.</p>
      <p><a href="/ejemplo_carga_nuam.csv" download>Descargar ejemplo de CSV</a></p>
      <input ref={input} type="file" accept=".csv,.xlsx" onChange={seleccionar} />
      {archivo && <p className="suave">Archivo seleccionado: {archivo.name}</p>}
      <div className="acciones"><button className="boton" onClick={previsualizar} disabled={ocupado || !archivo}>
        1. Validar y previsualizar</button>
        <button className="boton" onClick={confirmar} disabled={ocupado || !vista?.puede_confirmar}>
          2. Confirmar carga</button></div>
    </section>
    {error && <div className="alerta error" role="alert">{error}</div>}
    {mensaje && <div className="alerta exito">{mensaje}</div>}
    {vista && <section className="tarjeta">
      <h2>Vista previa ({vista.total} filas válidas)</h2>
      {vista.errores?.length > 0 && <div className="alerta error"><b>Errores encontrados:</b>
        <ul>{vista.errores.map((e, i) => <li key={i}>Fila {e.fila}, columna {e.columna}: {e.mensaje}</li>)}</ul>
      </div>}
      {vista.puede_confirmar && <div className="alerta exito">Archivo válido. Puedes confirmar el guardado.</div>}
      <div className="tabla-scroll"><table><thead><tr><th>Fila</th><th>RUT</th><th>Año</th><th>Monto</th><th>Factor</th></tr></thead>
        <tbody>{vista.filas.map((f, i) => <tr key={i}><td>{f.fila}</td><td>{f.rut}</td><td>{f.anio}</td>
          <td>{f.monto}</td><td>{f.factor}</td></tr>)}</tbody></table></div>
      {vista.total > 100 && <p className="suave">Se muestran las primeras 100 filas.</p>}
    </section>}
  </div>
}