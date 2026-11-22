from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .auth_views import obtener_csrf, iniciar_sesion, verificar_mfa, usuario_actual, cerrar_sesion
from .views import (CalificacionViewSet, vista_previa, confirmar_carga, periodos,
                    cerrar_periodo, historial, exportar_historial, auditoria,
                    resumen, usuarios, editar_usuario)

router = DefaultRouter()
router.register('calificaciones', CalificacionViewSet, basename='calificaciones')

urlpatterns = [
    path('auth/csrf/', obtener_csrf),
    path('auth/login/', iniciar_sesion),
    path('auth/mfa/', verificar_mfa),
    path('auth/me/', usuario_actual),
    path('auth/logout/', cerrar_sesion),
    path('cargas/preview/', vista_previa),
    path('cargas/confirmar/', confirmar_carga),
    path('periodos/', periodos),
    path('periodos/cerrar/', cerrar_periodo),
    path('historial/', historial),
    path('historial/exportar/', exportar_historial),
    path('auditoria/', auditoria),
    path('resumen/', resumen),
    path('usuarios/', usuarios),
    path('usuarios/<int:pk>/', editar_usuario),
    path('', include(router.urls)),
]