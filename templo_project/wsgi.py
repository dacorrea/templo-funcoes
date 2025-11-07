import os
from django.core.wsgi import get_wsgi_application
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'templo_project.settings')
django.setup()
try:
    call_command('migrate', interactive=False)
except Exception as e:
    print(f"Erro ao aplicar migrações: {e}")

application = get_wsgi_application()


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'templo_project.settings')
application = get_wsgi_application()
