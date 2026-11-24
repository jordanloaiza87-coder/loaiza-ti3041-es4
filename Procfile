release: python manage.py migrate && python manage.py loaddata productos.json
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
