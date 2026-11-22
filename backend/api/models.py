from django.conf import settings
from django.db import models


class Calificacion(models.Model):
    # Campos ya existentes en tu ZIP. El factor migra de texto a decimal exacto.
    rut = models.CharField(max_length=12)
    anio = models.IntegerField()
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    factor = models.DecimalField(max_digits=12, decimal_places=6, default=1)
    estado = models.CharField(max_length=50, default='Validado')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='calificaciones_creadas')
    actualizado_en = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-id']
        constraints = [models.UniqueConstraint(fields=['rut', 'anio'], name='calificacion_rut_anio_unico')]

    def __str__(self):
        return f'{self.rut} - {self.anio}'


class PerfilMFA(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    secreto = models.CharField(max_length=64)
    activado = models.BooleanField(default=False)
    ultimo_paso = models.BigIntegerField(default=-1)

    def __str__(self):
        return f'MFA de {self.usuario.username}'


class PeriodoTributario(models.Model):
    anio = models.IntegerField(unique=True)
    cerrado = models.BooleanField(default=False)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.anio} - {"Cerrado" if self.cerrado else "Abierto"}'


class CargaArchivo(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    nombre_archivo = models.CharField(max_length=255)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=30, default='Confirmada')
    total_filas = models.PositiveIntegerField(default=0)
    filas_validas = models.PositiveIntegerField(default=0)
    filas_rechazadas = models.PositiveIntegerField(default=0)
    hash_archivo = models.CharField(max_length=64)

    class Meta:
        ordering = ['-fecha']


class ErrorCarga(models.Model):
    carga = models.ForeignKey(CargaArchivo, on_delete=models.CASCADE, related_name='errores')
    numero_fila = models.PositiveIntegerField()
    campo = models.CharField(max_length=60)
    mensaje = models.CharField(max_length=255)


class RegistroAuditoria(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    calificacion = models.ForeignKey(Calificacion, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=60)
    detalle = models.TextField(blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_hora']

    def __str__(self):
        return f'{self.fecha_hora} - {self.accion}'