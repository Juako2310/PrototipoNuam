import { useEffect, useState } from 'react'
import { api, mensajeError } from '../api'

export default function Panel() {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/resumen/')
      .then(res => setDatos(res.data))
      .catch(e => setError(mensajeError(e)))
  }, [])

  // Evita errores cuando la API no entrega una lista
  const ultimasCargas = Array.isArray(datos?.ultimas_cargas)
    ? datos.ultimas_cargas
    : []

  return (
    <div>
      <h1>Panel principal</h1>

      <p className="suave">
        Resumen de la información cargada y de los períodos tributarios.
      </p>

      {error && (
        <div className="alerta error">{error}</div>
      )}

      {!datos ? (
        <p>{error ? 'No se pudo cargar el resumen.' : 'Cargando resumen...'}</p>
      ) : (
        <>
          <div className="cuadricula indicadores">
            <div className="tarjeta dato">
              <b>{datos.vigentes ?? 0}</b>
              <span>Calificaciones vigentes</span>
            </div>

            <div className="tarjeta dato">
              <b>{datos.cargas ?? 0}</b>
              <span>Cargas confirmadas</span>
            </div>

            <div className="tarjeta dato">
              <b>{datos.rechazadas ?? 0}</b>
              <span>Cargas rechazadas</span>
            </div>

            <div className="tarjeta dato">
              <b>{datos.periodos_cerrados ?? 0}</b>
              <span>Períodos cerrados</span>
            </div>
          </div>

          <section className="tarjeta">
            <h2>Últimos archivos procesados</h2>

            {ultimasCargas.length === 0 ? (
              <p>Aún no hay archivos para mostrar.</p>
            ) : (
              <div className="tabla-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Archivo</th>
                      <th>Registros</th>
                      <th>Estado</th>
                      <th>Fecha</th>
                    </tr>
                  </thead>

                  <tbody>
                    {ultimasCargas.map((c, i) => (
                      <tr key={i}>
                        <td>{c.archivo}</td>
                        <td>{c.total}</td>
                        <td>{c.estado}</td>
                        <td>{new Date(c.fecha).toLocaleString('es-CL')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="tarjeta">
            <h2>Cómo usar esta plataforma</h2>
            <p>
              En <b>Calificaciones</b> puedes buscar, crear y modificar
              registros; en <b>Carga masiva</b> puedes validar archivos
              y confirmar su ingreso; en <b>Historial anual</b> puedes
              consultar y exportar períodos cerrados sin editarlos.
            </p>
          </section>
        </>
      )}
    </div>
  )
}
