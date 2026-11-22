from getpass import getpass
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crea cuentas académicas para probar Administrador y Corredor.'

    def handle(self, *args, **kwargs):
        Usuario = get_user_model()
        for rol, nombre in [('Administrador', 'admin_demo'), ('Corredor', 'corredor_demo')]:
            grupo, _ = Group.objects.get_or_create(name=rol)
            self.stdout.write(f'\nCuenta {nombre} ({rol})')
            clave = getpass('Escribe una contraseña (mínimo 10 caracteres): ')
            confirmar = getpass('Repítela: ')
            if clave != confirmar:
                self.stderr.write('Las contraseñas no coinciden. No se modificó la cuenta.')
                continue
            usuario, creado = Usuario.objects.get_or_create(username=nombre)
            try:
                password_validation.validate_password(clave, usuario)
            except Exception as error:
                if creado:
                    usuario.delete()
                self.stderr.write('Contraseña no aceptada: ' + str(error))
                continue
            usuario.set_password(clave)
            usuario.is_active = True
            usuario.is_staff = False
            usuario.is_superuser = False
            usuario.save()
            usuario.groups.set([grupo])
            usuario.perfilmfa.delete() if hasattr(usuario, 'perfilmfa') else None
            self.stdout.write(self.style.SUCCESS(f'Cuenta {nombre} configurada.'))