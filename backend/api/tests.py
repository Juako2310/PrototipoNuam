import json
import pyotp
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from .models import Calificacion, PerfilMFA


class PruebasMantenedorNuam(TestCase):
    def setUp(self):
        Usuario = get_user_model()
        admin_grupo = Group.objects.create(name='Administrador')
        corredor_grupo = Group.objects.create(name='Corredor')
        self.admin = Usuario.objects.create_user('admin_prueba', password='ClaveSeguraDePrueba2026!')
        self.corredor = Usuario.objects.create_user('corredor_prueba', password='ClaveSeguraDePrueba2026!')
        self.admin.groups.add(admin_grupo)
        self.corredor.groups.add(corredor_grupo)
        for usuario in (self.admin, self.corredor):
            PerfilMFA.objects.create(usuario=usuario, secreto=pyotp.random_base32(), activado=True)
        self.cliente = Client(enforce_csrf_checks=True)

    def solicitud(self, ruta, datos):
        return self.cliente.post(ruta, data=json.dumps(datos), content_type='application/json',
                                 HTTP_X_CSRFTOKEN=self.cliente.cookies['csrftoken'].value)

    def entrar(self, usuario):
        self.cliente.get('/api/auth/csrf/')
        res = self.solicitud('/api/auth/login/', {
            'usuario': usuario.username, 'contrasena': 'ClaveSeguraDePrueba2026!'})
        self.assertEqual(res.status_code, 200)
        perfil = PerfilMFA.objects.get(usuario=usuario)
        res = self.solicitud('/api/auth/mfa/', {'codigo': pyotp.TOTP(perfil.secreto).now()})
        self.assertEqual(res.status_code, 200)

    def test_sin_login_no_hay_datos(self):
        self.assertEqual(self.cliente.get('/api/calificaciones/').status_code, 403)

    def test_login_mfa_y_restriccion_de_rol(self):
        self.entrar(self.corredor)
        self.assertEqual(self.cliente.get('/api/calificaciones/').status_code, 200)
        self.assertEqual(self.cliente.get('/api/usuarios/').status_code, 403)
        self.assertEqual(self.cliente.get('/api/auditoria/').status_code, 403)

    def test_crear_editar_baja_y_auditoria(self):
        self.entrar(self.admin)
        creado = self.solicitud('/api/calificaciones/', {
            'rut': '76.123.456-7', 'anio': 2026, 'monto': '15000.00', 'factor': '1.000000'})
        self.assertEqual(creado.status_code, 201, creado.content)
        pk = creado.json()['id']
        editado = self.cliente.put(f'/api/calificaciones/{pk}/',
                                  data=json.dumps({'rut': '76.123.456-7', 'anio': 2026,
                                                   'monto': '18000.00', 'factor': '1.250000'}),
                                  content_type='application/json',
                                  HTTP_X_CSRFTOKEN=self.cliente.cookies['csrftoken'].value)
        self.assertEqual(editado.status_code, 200, editado.content)
        borrado = self.cliente.delete(f'/api/calificaciones/{pk}/',
                                     HTTP_X_CSRFTOKEN=self.cliente.cookies['csrftoken'].value)
        self.assertEqual(borrado.status_code, 204, borrado.content)
        self.assertFalse(Calificacion.objects.get(pk=pk).activo)
        self.assertTrue(self.cliente.get('/api/auditoria/').json())

    def test_archivo_se_valida_antes_de_confirmar(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.entrar(self.corredor)
        csv_malo = b'rut,anio,monto,factor\n76.123.456-7,2026,1200,1\n77.234.567-8,2026,abc,1\n'
        res = self.cliente.post('/api/cargas/preview/', {
            'file': SimpleUploadedFile('malo.csv', csv_malo, content_type='text/csv')},
            HTTP_X_CSRFTOKEN=self.cliente.cookies['csrftoken'].value)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertFalse(res.json()['puede_confirmar'])
        self.assertEqual(Calificacion.objects.count(), 0)

    def test_historial_cerrado_no_permite_edicion(self):
        self.entrar(self.admin)
        self.solicitud('/api/calificaciones/', {
            'rut': '76.123.456-7', 'anio': 2025, 'monto': '15000.00', 'factor': '1.000000'})
        self.assertEqual(self.solicitud('/api/periodos/cerrar/', {'anio': 2025}).status_code, 200)
        self.assertEqual(self.cliente.get('/api/historial/?anio=2025').status_code, 200)
        intento = self.solicitud('/api/calificaciones/', {
            'rut': '77.234.567-8', 'anio': 2025, 'monto': '50.00', 'factor': '1.000000'})
        self.assertEqual(intento.status_code, 400)
        self.assertEqual(self.cliente.get('/api/historial/exportar/?anio=2025').status_code, 200)

    def test_carga_correcta_se_confirma_completa(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.entrar(self.admin)
        datos = b'rut,anio,monto,factor\n76.123.456-7,2026,1000.00,1.250000\n77.234.567-8,2026,2000.00,0.750000\n'
        def archivo():
            return SimpleUploadedFile('ejemplo.csv', datos, content_type='text/csv')
        previo = self.cliente.post('/api/cargas/preview/', {'file': archivo()},
                                   HTTP_X_CSRFTOKEN=self.cliente.cookies['csrftoken'].value)
        self.assertEqual(previo.status_code, 200, previo.content)
        self.assertTrue(previo.json()['puede_confirmar'], previo.content)
        self.assertEqual(Calificacion.objects.count(), 0)
        final = self.cliente.post('/api/cargas/confirmar/', {
            'file': archivo(), 'hash_archivo': previo.json()['hash_archivo']},
            HTTP_X_CSRFTOKEN=self.cliente.cookies['csrftoken'].value)
        self.assertEqual(final.status_code, 200, final.content)
        self.assertEqual(Calificacion.objects.count(), 2)

    def test_no_se_confirma_sin_vista_previa(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.entrar(self.corredor)
        contenido = b'rut,anio,monto,factor\n76.123.456-7,2026,1000.00,1.00\n'
        import hashlib
        respuesta = self.cliente.post('/api/cargas/confirmar/', {
            'file': SimpleUploadedFile('prueba.csv', contenido, content_type='text/csv'),
            'hash_archivo': hashlib.sha256(contenido).hexdigest()},
            HTTP_X_CSRFTOKEN=self.cliente.cookies['csrftoken'].value)
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Calificacion.objects.count(), 0)