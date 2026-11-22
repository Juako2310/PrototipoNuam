import { useEffect, useState } from 'react'
import { api, prepararCSRF, mensajeError } from './api'
import Login from './paginas/Login'
import Panel from './paginas/Panel'
import Mantenedor from './paginas/Mantenedor'
import Cargas from './paginas/Cargas'
import Historial from './paginas/Historial'
import Administracion from './paginas/Administracion'
import './estilos.css'

export default function App() {
  const [usuario, setUsuario] = useState(null)
  const [pantalla, setPantalla] = useState('panel')
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function comprobarSesion() {
      try {
        await prepararCSRF()
        const respuesta = await api.get('/auth/me/')
        setUsuario(respuesta.data)
      } catch (e) {
        if (e.response?.status !== 401) setError(mensajeError(e))
        setUsuario(null)
      } finally {
        setCargando(false)
      }
    }
    comprobarSesion()
  }, [])

  async function salir() {
    try {
      await api.post('/auth/logout/')
      setUsuario(null)
      setPantalla('panel')
    } catch (e) {
      setError(mensajeError(e))
    }
  }

  if (cargando) return <main className="centrado">Iniciando prototipo Nuam...</main>
  if (!usuario) return <Login alIngresar={(datos) => { setUsuario(datos); setError('') }} />

  const administrador = usuario.rol === 'Administrador'
  const secciones = [
    ['panel', 'Inicio'], ['mantenedor', 'Calificaciones'],
    ['cargas', 'Carga masiva'], ['historial', 'Historial anual'],
    ...(administrador ? [['administracion', 'Administración']] : []),
  ]

  return (
    <div className="aplicacion">
      <header className="cabecera">
        <div><div className="marca">NUAM <span>| Mantenedor Tributario</span></div>
          <small>Prototipo académico — datos ficticios</small>
        </div>
        <div className="sesion"><span>{usuario.usuario} · {usuario.rol}</span>
          <button className="boton secundario claro" onClick={salir}>Cerrar sesión</button>
        </div>
      </header>
      <div className="estructura">
        <nav className="menu" aria-label="Secciones del sistema">
          {secciones.map(([clave, titulo]) =>
            <button key={clave} className={pantalla === clave ? 'opcion activa' : 'opcion'}
              onClick={() => { setPantalla(clave); setError('') }}>{titulo}</button>)}
        </nav>
        <main className="contenido">
          {error && <div className="alerta error">{error}</div>}
          {pantalla === 'panel' && <Panel />}
          {pantalla === 'mantenedor' && <Mantenedor administrador={administrador} />}
          {pantalla === 'cargas' && <Cargas />}
          {pantalla === 'historial' && <Historial administrador={administrador} />}
          {pantalla === 'administracion' && administrador && <Administracion />}
        </main>
      </div>
    </div>
  )
}