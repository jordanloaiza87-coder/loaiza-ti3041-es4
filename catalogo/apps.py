import os
from django.apps import AppConfig
from django.db.models.signals import post_migrate


def poblar_productos_automatico(sender, **kwargs):
    """
    Carga automáticamente productos.json y asegura un superusuario por defecto
    tras ejecutar migrate si la base de datos está vacía (sin subir db.sqlite3 al repo).
    """
    from django.conf import settings
    from django.core.management import call_command
    from django.contrib.auth.models import User
    from .models import Producto
    try:
        if Producto.objects.count() == 0:
            fixture_path = os.path.join(settings.BASE_DIR, 'productos.json')
            if os.path.exists(fixture_path):
                call_command('loaddata', fixture_path, verbosity=0)

        if not User.objects.filter(username='jordanAdmin').exists():
            User.objects.create_superuser('jordanAdmin', 'jordan@ferreteriavi.cl', 'admin1234')
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@ferreteriavi.cl', 'admin1234')
    except Exception:
        pass


class CatalogoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalogo'

    def ready(self):
        post_migrate.connect(poblar_productos_automatico, sender=self)
