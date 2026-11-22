from rest_framework.permissions import BasePermission


def rol_de(usuario):
    if not usuario.is_authenticated or not usuario.is_active:
        return None
    if usuario.groups.filter(name='Administrador').exists():
        return 'Administrador'
    if usuario.groups.filter(name='Corredor').exists():
        return 'Corredor'
    return None


class EsUsuarioNuam(BasePermission):
    def has_permission(self, request, view):
        return rol_de(request.user) is not None


class EsAdministrador(BasePermission):
    def has_permission(self, request, view):
        return rol_de(request.user) == 'Administrador'