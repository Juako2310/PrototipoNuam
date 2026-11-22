import { useState } from 'react'
import { api, mensajeError } from '../api'

export default function Login({ alIngresar }) {
  const [usuario, setUsuario] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [codigo, setCodigo] = useState('')
  const [paso, setPaso] = useState('clave')
  const [registroMfa, setRegistroMfa] = useState(null)
  const [mensaje, setMensaje] = useState('')
  const [ocupado, setOcupado] = useState(false)

  async function enviarClave(e) {
    e.preventDefault()
    setMensaje(''); setOcupado(true)
    try {
      const respuesta = await api.post('/auth/login/', { usuario, contrasena })
      setRegistroMfa(respuesta.data)
      setContrasena('')
      setPaso('mfa')
    } catch (error) { setMensaje(mensajeError(error)) }
    finally { setOcupado(false) }
  }

  async function enviarCodigo(e) {
    e.preventDefault()
    setMensaje(''); setOcupado(true)
    try {
      const respuesta = await api.post('/auth/mfa/', { codigo })
      alIngresar(respuesta.data)
    } catch (error) { setMensaje(mensajeError(error)) }
    finally { setOcupado(false) }
  }

  return (
    <div className="pantalla-login">
      <section className="tarjeta login">
        <div className="logo-login">NUAM</div>
        <h1>Mantenedor de Calificaciones Tributarias</h1>
        <p className="suave">Acceso exclusivo para corredores y administradores autorizados.</p>
        {mensaje && <div className="alerta error" role="alert">{mensaje}</div>}
        {paso === 'clave' ? (
          <form onSubmit={enviarClave} className="formulario">
            <label>Usuario<input value={usuario} onChange={e => setUsuario(e.target.value)}
              autoComplete="username" required placeholder="admin_demo" /></label>
            <label>Contraseña<input type="password" value={contrasena}
              onChange={e => setContrasena(e.target.value)} autoComplete="current-password" required /></label>
            <button className="boton" disabled={ocupado}>Continuar</button>
          </form>
        ) : (
          <form onSubmit={enviarCodigo} className="formulario">
            <h2>Segundo factor de seguridad</h2>
            {registroMfa?.configurar_mfa && (
              <div className="alerta informacion">
                <b>Primera vez:</b> abre Google Authenticator, Microsoft Authenticator o una app TOTP.
                Elige <b>Agregar cuenta → Introducir clave de configuración</b>.
                <p>Nombre: Nuam Prototipo ({usuario})</p>
                <p>Clave secreta: <code className="secreto">{registroMfa.secreto_mfa}</code></p>
                <small>No compartas esta clave. En una implementación real debe almacenarse cifrada.</small>
              </div>
            )}
            <label>Código de 6 números<input value={codigo} onChange={e => setCodigo(e.target.value)}
              type="text" inputMode="numeric" maxLength="6" pattern="[0-9]{6}"
              autoComplete="one-time-code" placeholder="000000" required /></label>
            <button className="boton" disabled={ocupado}>Verificar e ingresar</button>
            <button type="button" className="boton secundario" onClick={() => {
              setPaso('clave'); setCodigo(''); setMensaje('')
            }}>Volver al inicio</button>
          </form>
        )}
        <p className="pie-login">Demostración local. No cargar datos tributarios reales.</p>
      </section>
    </div>
  )
}