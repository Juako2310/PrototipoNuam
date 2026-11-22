import axios from 'axios'


export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

export async function prepararCSRF() {
  await api.get('/auth/csrf/')
}

export function mensajeError(error) {
  const datos = error.response?.data
  if (!datos) return 'No se pudo conectar con Django. Revisa la terminal del backend.'
  if (typeof datos.error === 'string') return datos.error
  if (typeof datos.detail === 'string') return datos.detail
  const mensajes = []
  for (const [campo, valor] of Object.entries(datos)) {
    if (Array.isArray(valor)) mensajes.push(`${campo}: ${valor.join(', ')}`)
    else if (typeof valor === 'string') mensajes.push(`${campo}: ${valor}`)
  }
  return mensajes.join(' | ') || 'Ocurrió un error inesperado.'
}