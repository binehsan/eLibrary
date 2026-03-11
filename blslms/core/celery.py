from celery import Celery
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blslms.settings')

app = Celery('blslms')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Backward compatibility for existing imports
celeryapp = app
