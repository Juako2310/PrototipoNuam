import json
import time
from hmac import compare_digest

import pyotp
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from .models import PerfilMFA, RegistroAuditoria
from .permissions import rol_de


@ensure_csrf_cookie
@require_GET
def obtener_csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


def _datos(request):
    try:
        return json.loads(request.body.decode('utf-8'))
    except (UnicodeError, ValueError):
        return {}


@csrf_protect
@require_POST
def iniciar_sesion(request):
    datos = _datos(request)
    nombre = str(datos.get('usuario', '')).strip()
    contrasena = str(datos.get('contrasena', ''))
    if not nombre or not contrasena:
        return JsonResponse({'error': 'Ingresa tu usuario y contraseña.'}, status=400)

    clave = f'intentos:{request.META.get("REMOTE_ADDR", "local")}:{nombre.lower()}'
    intentos = cache.get(clave, 0)
    if intentos >= 5:
        return JsonResponse({'error': 'Demasiados intentos. Intenta de nuevo en 5 minutos.'}, status=429)

    usuario = authenticate(request, username=nombre, password=contrasena)
    if not usuario or not rol_de(usuario):
        cache.set(clave, intentos + 1, timeout=300)
        return JsonResponse({'error': 'Credenciales incorrectas o cuenta sin rol.'}, status=401)

    cache.delete(clave)
    perfil, _ = PerfilMFA.objects.get_or_create(usuario=usuario,
                                                 defaults={'secreto': pyotp.random_base32()})
    request.session['preauth_id'] = usuario.pk
    request.session['preauth_inicio'] = time.time()
    request.session['preauth_intentos'] = 0
    request.session.set_expiry(300)
    respuesta = {'requiere_mfa': True, 'configurar_mfa': not perfil.activado}
    if not perfil.activado:
        respuesta['secreto_mfa'] = perfil.secreto
        respuesta['uri_mfa'] = pyotp.TOTP(perfil.secreto).provisioning_uri(
            name=usuario.username, issuer_name='Nuam Prototipo')
    return JsonResponse(respuesta)


@csrf_protect
@require_POST
def verificar_mfa(request):
    usuario_id = request.session.get('preauth_id')
    inicio = request.session.get('preauth_inicio', 0)
    intentos = request.session.get('preauth_intentos', 0)
    if not usuario_id or time.time() - inicio > 300:
        return JsonResponse({'error': 'La verificación venció. Inicia sesión nuevamente.'}, status=401)
    if intentos >= 5:
        request.session.flush()
        return JsonResponse({'error': 'Demasiados códigos incorrectos.'}, status=429)
    codigo = str(_datos(request).get('codigo', '')).strip()
    if len(codigo) != 6 or not codigo.isdigit():
        return JsonResponse({'error': 'Ingresa el código de seis dígitos.'}, status=400)

    usuario = get_user_model().objects.filter(pk=usuario_id, is_active=True).first()
    if not usuario or not rol_de(usuario):
        request.session.flush()
        return JsonResponse({'error': 'Usuario sin acceso.'}, status=403)

    with transaction.atomic():
        perfil = PerfilMFA.objects.select_for_update().get(usuario=usuario)
        totp = pyotp.TOTP(perfil.secreto)
        paso_actual = int(time.time() // 30)
        valido_en = None
        for desplazamiento in (-1, 0, 1):
            paso = paso_actual + desplazamiento
            if paso > perfil.ultimo_paso and compare_digest(totp.at(paso * 30), codigo):
                valido_en = paso
                break
        if valido_en is None:
            request.session['preauth_intentos'] = intentos + 1
            return JsonResponse({'error': 'Código inválido, vencido o ya utilizado.'}, status=401)
        perfil.ultimo_paso = valido_en
        perfil.activado = True
        perfil.save(update_fields=['ultimo_paso', 'activado'])

    login(request, usuario)
    for campo in ('preauth_id', 'preauth_inicio', 'preauth_intentos'):
        request.session.pop(campo, None)
    request.session.set_expiry(1800)
    RegistroAuditoria.objects.create(usuario=usuario, accion='LOGIN', detalle='Ingreso MFA exitoso')
    return JsonResponse({'usuario': usuario.username, 'rol': rol_de(usuario)})


@require_GET
def usuario_actual(request):
    rol = rol_de(request.user)
    if not rol:
        return JsonResponse({'autenticado': False}, status=401)
    return JsonResponse({'autenticado': True, 'usuario': request.user.username, 'rol': rol})


@csrf_protect
@require_POST
def cerrar_sesion(request):
    if not rol_de(request.user):
        return JsonResponse({'error': 'No hay sesión abierta.'}, status=401)
    RegistroAuditoria.objects.create(usuario=request.user, accion='LOGOUT', detalle='Salida del sistema')
    logout(request)
    return JsonResponse({'mensaje': 'Sesión cerrada.'})