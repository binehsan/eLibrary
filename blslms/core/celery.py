from celery import Celery
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blslms.settings') #AIC
celeryapp = Celery()
celeryapp.config_from_object("django.conf:settings", namespace="CELERY")
celeryapp.autodiscover_tasks()
