from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def completar_fechas(apps, schema_editor):
    from django.utils import timezone
    Calificacion = apps.get_model('api', 'Calificacion')
    Calificacion.objects.filter(actualizado_en__isnull=True).update(actualizado_en=timezone.now())


def normalizar_factor(apps, schema_editor):
    Calificacion = apps.get_model('api', 'Calificacion')
    for cal in Calificacion.objects.all().iterator():
        original = str(cal.factor).strip().replace(',', '.')
        try:
            numero = Decimal(original)
            if not numero.is_finite() or numero <= 0:
                raise InvalidOperation
        except InvalidOperation:
            raise ValueError(f'Factor inválido en calificación id={cal.id}. Corrige los datos antes de migrar.')
        cal.factor = format(numero, 'f')
        cal.save(update_fields=['factor'])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(name='calificacion', options={'ordering': ['-id']}),
        migrations.RunPython(normalizar_factor, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='calificacion', name='factor',
            field=models.DecimalField(decimal_places=6, default=1, max_digits=12),
        ),
        migrations.AddField(
            model_name='calificacion', name='creado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='calificaciones_creadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='calificacion', name='actualizado_en',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name='calificacion', name='activo',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='PerfilMFA', fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('secreto', models.CharField(max_length=64)),
                ('activado', models.BooleanField(default=False)),
                ('ultimo_paso', models.BigIntegerField(default=-1)),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PeriodoTributario', fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anio', models.IntegerField(unique=True)),
                ('cerrado', models.BooleanField(default=False)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='CargaArchivo', fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_archivo', models.CharField(max_length=255)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('estado', models.CharField(default='Confirmada', max_length=30)),
                ('total_filas', models.PositiveIntegerField(default=0)),
                ('filas_validas', models.PositiveIntegerField(default=0)),
                ('filas_rechazadas', models.PositiveIntegerField(default=0)),
                ('hash_archivo', models.CharField(max_length=64)),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ], options={'ordering': ['-fecha']},
        ),
        migrations.CreateModel(
            name='RegistroAuditoria', fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accion', models.CharField(max_length=60)),
                ('detalle', models.TextField(blank=True)),
                ('fecha_hora', models.DateTimeField(auto_now_add=True)),
                ('calificacion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.calificacion')),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ], options={'ordering': ['-fecha_hora']},
        ),
        migrations.CreateModel(
            name='ErrorCarga', fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_fila', models.PositiveIntegerField()),
                ('campo', models.CharField(max_length=60)),
                ('mensaje', models.CharField(max_length=255)),
                ('carga', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='errores', to='api.cargaarchivo')),
            ],
        ),
        migrations.AddConstraint(
            model_name='calificacion',
            constraint=models.UniqueConstraint(fields=['rut', 'anio'], name='calificacion_rut_anio_unico'),
        ),
        migrations.RunPython(completar_fechas, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='calificacion', name='actualizado_en',
            field=models.DateTimeField(auto_now=True),
        ),
    ]