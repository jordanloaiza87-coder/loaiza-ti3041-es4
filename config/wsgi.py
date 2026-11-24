"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Auto-inicialización para servidores en la nube (Render, Railway, etc.)
try:
    from django.conf import settings
    from django.core.management import call_command
    from catalogo.models import Producto

    try:
        total = Producto.objects.count()
    except Exception:
        call_command('migrate', interactive=False, verbosity=0)
        total = Producto.objects.count()

    if total == 0:
        fixture_path = os.path.join(settings.BASE_DIR, 'productos.json')
        if os.path.exists(fixture_path):
            call_command('loaddata', fixture_path, verbosity=0)

    if not os.path.exists(settings.STATIC_ROOT):
        call_command('collectstatic', interactive=False, verbosity=0)
except Exception:
    pass
