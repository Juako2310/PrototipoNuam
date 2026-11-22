"""API del mantenedor. Las reglas de permisos se aplican en el servidor."""
import csv
import hashlib
import io
import time
import unicodedata
from decimal import Decimal

from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from openpyxl import Workbook, load_workbook
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import (Calificacion, CargaArchivo, ErrorCarga,
                     PeriodoTributario, RegistroAuditoria)
from .permissions import EsAdministrador, EsUsuarioNuam, rol_de
from .serializers import CalificacionSerializer


def esta_cerrado(anio):
    return PeriodoTributario.objects.filter(anio=anio, cerrado=True).exists()


def exigir_abierto(anio):
    if esta_cerrado(anio):
        raise ValidationError({'anio': ['El período está cerrado: solo lectura.']})


def auditar(usuario, accion, detalle, calificacion=None):
    return RegistroAuditoria.objects.create(
        usuario=usuario, accion=accion, detalle=detalle, calificacion=calificacion)


class CalificacionViewSet(viewsets.ModelViewSet):
    serializer_class = CalificacionSerializer
    permission_classes = [EsUsuarioNuam]
    queryset = Calificacion.objects.all()

    def get_queryset(self):
        cerrados = PeriodoTributario.objects.filter(cerrado=True).values('anio')
        consulta = Calificacion.objects.filter(activo=True).exclude(anio__in=cerrados)
        rut = self.request.query_params.get('rut', '').strip()
        anio = self.request.query_params.get('anio', '').strip()
        if rut:
            consulta = consulta.filter(rut__icontains=rut)
        if anio:
            if not anio.isdigit():
                return consulta.none()
            consulta = consulta.filter(anio=int(anio))
        return consulta.order_by('-id')

    @transaction.atomic
    def perform_create(self, serializer):
        exigir_abierto(serializer.validated_data['anio'])
        calificacion = serializer.save(creado_por=self.request.user)
        auditar(self.request.user, 'CREAR', f'{calificacion.rut} / {calificacion.anio}', calificacion)

    @transaction.atomic
    def perform_update(self, serializer):
        exigir_abierto(serializer.instance.anio)
        exigir_abierto(serializer.validated_data.get('anio', serializer.instance.anio))
        anterior = f'{serializer.instance.rut} / {serializer.instance.anio}'
        calificacion = serializer.save()
        auditar(self.request.user, 'EDITAR', f'{anterior} → {calificacion.rut} / {calificacion.anio}', calificacion)

    @transaction.atomic
    def perform_destroy(self, instance):
        if rol_de(self.request.user) != 'Administrador':
            raise PermissionDenied('Solo el administrador puede dar de baja registros.')
        exigir_abierto(instance.anio)
        instance.activo = False
        instance.estado = 'Dado de baja'
        instance.save(update_fields=['activo', 'estado', 'actualizado_en'])
        auditar(self.request.user, 'BAJA', f'{instance.rut} / {instance.anio}', instance)

    @action(detail=False, methods=['get'], url_path='bajas')
    def bajas(self, request):
        if rol_de(request.user) != 'Administrador':
            raise PermissionDenied('Solo administrador.')
        consulta = Calificacion.objects.filter(activo=False).order_by('-id')[:100]
        return Response(self.get_serializer(consulta, many=True).data)

    @action(detail=True, methods=['post'], url_path='restaurar')
    @transaction.atomic
    def restaurar(self, request, pk=None):
        if rol_de(request.user) != 'Administrador':
            raise PermissionDenied('Solo administrador.')
        registro = get_object_or_404(Calificacion, pk=pk, activo=False)
        exigir_abierto(registro.anio)
        registro.activo = True
        registro.estado = 'Validado'
        registro.save(update_fields=['activo', 'estado', 'actualizado_en'])
        auditar(request.user, 'RESTAURAR', f'{registro.rut} / {registro.anio}', registro)
        return Response(self.get_serializer(registro).data)


def _normalizar_encabezado(valor):
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    resultado = ''.join(c for c in texto if not unicodedata.combining(c)).strip().lower()
    return 'anio' if resultado in ('ano', 'anio', 'ano_tributario', 'anio_tributario') else resultado


def _leer_archivo(archivo):
    """Devuelve (filas, hash, errores). No escribe calificaciones."""
    if not archivo:
        return [], '', [{'fila': 0, 'columna': 'archivo', 'mensaje': 'Selecciona un archivo.'}]
    nombre = archivo.name.lower()
    if not nombre.endswith(('.csv', '.xlsx')):
        return [], '', [{'fila': 0, 'columna': 'archivo', 'mensaje': 'Solo CSV o XLSX.'}]
    if archivo.size > 2 * 1024 * 1024:
        return [], '', [{'fila': 0, 'columna': 'archivo', 'mensaje': 'Máximo 2 MB.'}]

    contenido = archivo.read()
    huella = hashlib.sha256(contenido).hexdigest()
    errores = []
    filas = []
    try:
        if nombre.endswith('.csv'):
            texto = contenido.decode('utf-8-sig')
            primera = texto.splitlines()[0] if texto.splitlines() else ''
            separador = ';' if primera.count(';') > primera.count(',') else ','
            lector = csv.reader(io.StringIO(texto), delimiter=separador)
            tabla = iter(lector)
        else:
            libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True, keep_links=False)
            tabla = libro.active.iter_rows(values_only=True)
        encabezados = next(tabla, None)
        if not encabezados:
            return [], huella, [{'fila': 1, 'columna': 'encabezados', 'mensaje': 'Archivo vacío.'}]
        encabezados = [_normalizar_encabezado(c) for c in encabezados]
        requeridos = ['rut', 'anio', 'monto']
        for obligatorio in requeridos:
            if obligatorio not in encabezados:
                errores.append({'fila': 1, 'columna': obligatorio,
                                'mensaje': f'Falta la columna {obligatorio}.'})
        if len(set(encabezados)) != len(encabezados):
            errores.append({'fila': 1, 'columna': 'encabezados', 'mensaje': 'Hay columnas repetidas.'})
        if errores:
            return [], huella, errores
        repetidos_archivo = set()
        for numero, valores in enumerate(tabla, start=2):
            if numero > 1001:
                errores.append({'fila': numero, 'columna': 'archivo', 'mensaje': 'Máximo 1000 filas de datos.'})
                break
            if not valores or all(v is None or str(v).strip() == '' for v in valores):
                continue
            datos = dict(zip(encabezados, valores))
            limpio = {}
            for campo in ('rut', 'anio', 'monto', 'factor'):
                valor = datos.get(campo, '')
                if valor is None:
                    valor = ''
                valor = str(valor).strip()
                if campo in ('monto', 'factor'):
                    valor = valor.replace(',', '.')
                if campo == 'factor' and not valor:
                    valor = '1.000000'
                limpio[campo] = valor
            serializador = CalificacionSerializer(data=limpio)
            if not serializador.is_valid():
                for campo, mensajes in serializador.errors.items():
                    for mensaje in mensajes:
                        errores.append({'fila': numero, 'columna': campo, 'mensaje': str(mensaje)})
                continue
            normalizado = serializador.validated_data
            llave = (normalizado['rut'], normalizado['anio'])
            if llave in repetidos_archivo:
                errores.append({'fila': numero, 'columna': 'rut/anio',
                                'mensaje': 'RUT y año repetidos dentro del archivo.'})
            repetidos_archivo.add(llave)
            if esta_cerrado(normalizado['anio']):
                errores.append({'fila': numero, 'columna': 'anio', 'mensaje': 'Año cerrado; no admite cargas.'})
            filas.append({'rut': normalizado['rut'], 'anio': normalizado['anio'],
                          'monto': str(normalizado['monto']),
                          'factor': str(normalizado['factor']), 'fila': numero})
        if not filas and not errores:
            errores.append({'fila': 2, 'columna': 'archivo', 'mensaje': 'No hay filas para cargar.'})
    except (UnicodeError, csv.Error, ValueError, TypeError, OSError, KeyError, IndexError) as error:
        errores.append({'fila': 0, 'columna': 'archivo',
                        'mensaje': f'No se pudo leer el archivo: {type(error).__name__}.'})
    except Exception:
        # openpyxl también puede fallar si el XLSX está dañado.
        errores.append({'fila': 0, 'columna': 'archivo', 'mensaje': 'Archivo Excel/CSV ilegible.'})
    return filas, huella, errores


@api_view(['POST'])
@permission_classes([EsUsuarioNuam])
def vista_previa(request):
    filas, huella, errores = _leer_archivo(request.FILES.get('file'))
    if not errores and filas:
        request.session['preview_hash'] = huella
        request.session['preview_expira'] = time.time() + 300
    else:
        request.session.pop('preview_hash', None)
        request.session.pop('preview_expira', None)
    return Response({'filas': filas[:100], 'total': len(filas), 'hash_archivo': huella,
                     'errores': errores, 'puede_confirmar': len(errores) == 0 and len(filas) > 0})


@api_view(['POST'])
@permission_classes([EsUsuarioNuam])
def confirmar_carga(request):
    archivo = request.FILES.get('file')
    filas, huella, errores = _leer_archivo(archivo)
    confirmado = str(request.data.get('hash_archivo', ''))
    if (huella != confirmado or not huella or
            request.session.get('preview_hash') != huella or
            time.time() > request.session.get('preview_expira', 0)):
        return Response({'error': 'Necesitas validar de nuevo el archivo en vista previa.'}, status=400)
    if errores:
        with transaction.atomic():
            carga = CargaArchivo.objects.create(
                usuario=request.user, nombre_archivo=archivo.name[:255],
                total_filas=len(filas), filas_validas=0, filas_rechazadas=len(errores),
                hash_archivo=huella, estado='Rechazada')
            ErrorCarga.objects.bulk_create([
                ErrorCarga(carga=carga, numero_fila=e['fila'], campo=e['columna'], mensaje=e['mensaje'][:255])
                for e in errores
            ])
            auditar(request.user, 'CARGA_RECHAZADA', archivo.name[:255])
        return Response({'error': 'Se rechazó todo el archivo. Corrige los errores.',
                         'errores': errores}, status=400)
    if not filas:
        return Response({'error': 'El archivo está vacío.'}, status=400)

    try:
        with transaction.atomic():
            # Revalidar dentro de la transacción evita aceptar cambios de períodos a destiempo.
            for fila in filas:
                exigir_abierto(fila['anio'])
            carga = CargaArchivo.objects.create(
                usuario=request.user, nombre_archivo=archivo.name[:255],
                total_filas=len(filas), filas_validas=len(filas), filas_rechazadas=0,
                hash_archivo=huella, estado='Confirmada')
            objetos = [Calificacion(rut=fila['rut'], anio=fila['anio'],
                                    monto=Decimal(fila['monto']), factor=Decimal(fila['factor']),
                                    creado_por=request.user)
                       for fila in filas]
            # UNIQUE(rut, anio): si existe una fila duplicada, no se guarda ninguna.
            Calificacion.objects.bulk_create(objetos)
            auditar(request.user, 'CARGA_CONFIRMADA',
                    f'Carga {carga.id}: {len(filas)} registros desde {archivo.name[:200]}')
    except IntegrityError:
        return Response({'error': 'Hay un RUT/año que ya existe. No se guardó ninguna fila.'}, status=409)
    except ValidationError as error:
        return Response({'error': 'La carga incluye períodos cerrados.', 'detalle': error.detail}, status=400)
    request.session.pop('preview_hash', None)
    request.session.pop('preview_expira', None)
    return Response({'mensaje': f'Se guardaron {len(filas)} registros.', 'total': len(filas)})


@api_view(['GET'])
@permission_classes([EsUsuarioNuam])
def periodos(request):
    anios = set(Calificacion.objects.values_list('anio', flat=True))
    anios.update(PeriodoTributario.objects.values_list('anio', flat=True))
    cerrados = set(PeriodoTributario.objects.filter(cerrado=True).values_list('anio', flat=True))
    return Response([{'anio': a, 'cerrado': a in cerrados} for a in sorted(anios, reverse=True)])


@api_view(['POST'])
@permission_classes([EsAdministrador])
def cerrar_periodo(request):
    try:
        anio = int(request.data.get('anio'))
    except (ValueError, TypeError):
        return Response({'error': 'Año inválido.'}, status=400)
    if not 2000 <= anio <= 2100:
        return Response({'error': 'Año fuera de rango.'}, status=400)
    with transaction.atomic():
        periodo, _ = PeriodoTributario.objects.get_or_create(anio=anio)
        if periodo.cerrado:
            return Response({'error': 'El año ya estaba cerrado.'}, status=400)
        periodo.cerrado = True
        periodo.save(update_fields=['cerrado', 'actualizado_en'])
        auditar(request.user, 'CERRAR_PERIODO', f'Año {anio}')
    return Response({'mensaje': f'Período {anio} cerrado y protegido contra modificaciones.'})


@api_view(['GET'])
@permission_classes([EsUsuarioNuam])
def historial(request):
    valor = request.query_params.get('anio', '')
    if not valor.isdigit():
        return Response({'error': 'Selecciona un año cerrado.'}, status=400)
    anio = int(valor)
    if not esta_cerrado(anio):
        return Response({'error': 'Solo puedes consultar años cerrados en el historial.'}, status=400)
    items = Calificacion.objects.filter(anio=anio).order_by('rut')[:5000]
    return Response(CalificacionSerializer(items, many=True).data)


@api_view(['GET'])
@permission_classes([EsUsuarioNuam])
def exportar_historial(request):
    valor = request.query_params.get('anio', '')
    if not valor.isdigit() or not esta_cerrado(int(valor)):
        return Response({'error': 'Selecciona un año cerrado.'}, status=400)
    anio = int(valor)
    formato = request.query_params.get('formato', 'csv').lower()
    if formato not in ('csv', 'xlsx'):
        return Response({'error': 'Formato de exportación no admitido.'}, status=400)
    registros = Calificacion.objects.filter(anio=anio).order_by('rut')
    encabezados = ['rut', 'anio', 'monto', 'factor', 'estado', 'activo']
    if formato == 'xlsx':
        libro = Workbook()
        hoja = libro.active
        hoja.title = f'Historial {anio}'
        hoja.append(encabezados)
        for c in registros.iterator():
            # Evitar conversiones a float para preservar decimales exactos.
            hoja.append([c.rut, c.anio, str(c.monto), str(c.factor), c.estado, c.activo])
        temporal = io.BytesIO()
        libro.save(temporal)
        salida = HttpResponse(temporal.getvalue(), content_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
        salida['Content-Disposition'] = f'attachment; filename="historial_nuam_{anio}.xlsx"'
    else:
        salida = HttpResponse(content_type='text/csv; charset=utf-8')
        salida['Content-Disposition'] = f'attachment; filename="historial_nuam_{anio}.csv"'
        salida.write('\ufeff')
        escritor = csv.writer(salida)
        escritor.writerow(encabezados)
        for c in registros.iterator():
            escritor.writerow([c.rut, c.anio, c.monto, c.factor, c.estado, c.activo])
    auditar(request.user, 'EXPORTAR_HISTORIAL', f'Año {anio} / {formato}')
    return salida


@api_view(['GET'])
@permission_classes([EsAdministrador])
def auditoria(request):
    registros = RegistroAuditoria.objects.select_related('usuario').all()
    usuario = request.query_params.get('usuario', '').strip()
    accion = request.query_params.get('accion', '').strip()
    fecha = request.query_params.get('fecha', '').strip()
    if fecha:
        try:
            from datetime import date
            fecha_consulta = date.fromisoformat(fecha)
            registros = registros.filter(fecha_hora__date=fecha_consulta)
        except ValueError:
            return Response({'error': 'Formato de fecha inválido.'}, status=400)
    if usuario:
        registros = registros.filter(usuario__username__icontains=usuario)
    if accion:
        registros = registros.filter(accion__icontains=accion)
    return Response([{'id': r.id, 'usuario': r.usuario.username if r.usuario else 'Desconocido',
                      'accion': r.accion, 'detalle': r.detalle, 'fecha': r.fecha_hora}
                     for r in registros[:200]])


@api_view(['GET'])
@permission_classes([EsUsuarioNuam])
def resumen(request):
    return Response({
        'vigentes': Calificacion.objects.filter(activo=True).count(),
        'periodos_cerrados': PeriodoTributario.objects.filter(cerrado=True).count(),
        'cargas': CargaArchivo.objects.filter(estado='Confirmada').count(),
        'rechazadas': CargaArchivo.objects.filter(estado='Rechazada').count(),
        'ultimas_cargas': [{'archivo': c.nombre_archivo, 'total': c.total_filas,
                           'estado': c.estado, 'fecha': c.fecha}
                          for c in CargaArchivo.objects.all()[:5]],
    })


def _usuario_publico(usuario):
    return {'id': usuario.pk, 'usuario': usuario.username, 'email': usuario.email,
            'activo': usuario.is_active, 'rol': rol_de(usuario) or 'Sin rol'}


@api_view(['GET', 'POST'])
@permission_classes([EsAdministrador])
def usuarios(request):
    Usuario = get_user_model()
    if request.method == 'GET':
        return Response([_usuario_publico(u) for u in Usuario.objects.all().order_by('username')[:100]])
    nombre = str(request.data.get('usuario', '')).strip()
    email = str(request.data.get('email', '')).strip()
    clave = str(request.data.get('contrasena', ''))
    rol = str(request.data.get('rol', ''))
    if rol not in ('Corredor', 'Administrador') or not nombre or not clave:
        return Response({'error': 'Completa usuario, contraseña y rol válido.'}, status=400)
    if Usuario.objects.filter(username=nombre).exists():
        return Response({'error': 'El usuario ya existe.'}, status=400)
    if email and Usuario.objects.filter(email__iexact=email).exists():
        return Response({'error': 'El correo ya está en uso.'}, status=400)
    temporal = Usuario(username=nombre, email=email)
    try:
        password_validation.validate_password(clave, temporal)
    except Exception as error:
        return Response({'error': 'Contraseña no aceptada: ' + str(error)}, status=400)
    with transaction.atomic():
        usuario = Usuario.objects.create_user(username=nombre, email=email, password=clave)
        grupo, _ = Group.objects.get_or_create(name=rol)
        usuario.groups.set([grupo])
        auditar(request.user, 'CREAR_USUARIO', f'{nombre} / {rol}')
    return Response(_usuario_publico(usuario), status=201)


@api_view(['PATCH'])
@permission_classes([EsAdministrador])
def editar_usuario(request, pk):
    Usuario = get_user_model()
    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario == request.user and request.data.get('activo') is False:
        return Response({'error': 'No puedes desactivar tu propia cuenta.'}, status=400)
    rol = request.data.get('rol')
    if rol is not None and rol not in ('Administrador', 'Corredor'):
        return Response({'error': 'Rol inválido.'}, status=400)
    with transaction.atomic():
        if rol is not None:
            grupo, _ = Group.objects.get_or_create(name=rol)
            usuario.groups.set([grupo])
        if 'activo' in request.data:
            if not isinstance(request.data['activo'], bool):
                return Response({'error': 'El campo activo debe ser verdadero o falso.'}, status=400)
            usuario.is_active = request.data['activo']
        usuario.save()
        auditar(request.user, 'EDITAR_USUARIO', f'{usuario.username} / {rol or rol_de(usuario)} / activo={usuario.is_active}')
    return Response(_usuario_publico(usuario))