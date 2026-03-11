# BLS eLibrary — Operations Guide

## Architecture overview

```
Browser → nginx (443/80) → gunicorn.sock → Django (blslms.wsgi)
                                            ↕
                                      Redis (6379)
                                            ↕
                              Celery worker  +  Celery beat
```

---

## 1. Required services

| Service        | Unit name       | Must be running | Purpose                        |
|----------------|-----------------|-----------------|--------------------------------|
| Redis          | `redis`         | **Yes**         | Celery broker + result backend |
| Gunicorn       | `gunicorn`      | **Yes**         | Serves Django over WSGI        |
| Celery worker  | `celery`        | **Yes**         | Executes background tasks      |
| Celery beat    | `celerybeat`    | **Yes**         | Schedules periodic tasks       |
| nginx          | `nginx`         | **Yes**         | Reverse proxy, static/media    |

### Quick health check

```bash
sudo systemctl status redis gunicorn celery celerybeat nginx --no-pager
```

### Restart all

```bash
sudo systemctl restart redis gunicorn celery celerybeat
sudo systemctl reload nginx
```

---

## 2. Redis

Redis is the message broker for Celery. Without it, **no background tasks will run**.

```bash
# Check Redis
redis-cli ping            # → PONG
systemctl is-active redis # → active

# Start / enable on boot
sudo systemctl enable --now redis
```

Settings reference (`blslms/settings.py`):
```
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
```

---

## 3. Gunicorn

Gunicorn serves the Django app behind nginx via a Unix socket.

```bash
# Check status
sudo systemctl status gunicorn --no-pager

# Restart after code changes
sudo systemctl restart gunicorn

# Logs
sudo journalctl -u gunicorn -f
```

The socket is at `/run/gunicorn.sock`. nginx proxies to it.

---

## 4. Celery

### Worker (executes tasks)
```bash
sudo systemctl status celery --no-pager
sudo journalctl -u celery -f           # live logs
sudo systemctl restart celery           # after code changes
```

### Beat (scheduler — triggers periodic tasks)
```bash
sudo systemctl status celerybeat --no-pager
sudo journalctl -u celerybeat -f
sudo systemctl restart celerybeat
```

### Common issues

| Symptom                                     | Cause                             | Fix                                     |
|---------------------------------------------|-----------------------------------|-----------------------------------------|
| `AttributeError: 'NoneType' … 'Redis'`     | Python `redis` package missing    | `pip install redis` in the venv         |
| `SMTPAuthenticationError 535`               | Wrong email credentials in env    | Update `NOREPLY_PWD` in `/etc/blslms.env` |
| Tasks silently not running                  | Beat or worker not started        | `sudo systemctl start celery celerybeat`|
| `ModuleNotFoundError`                       | Venv missing a dependency         | `pip install -r requirements.txt`       |

---

## 5. Logs

### Django application logs (file-based)

| File                        | Content                           |
|-----------------------------|-----------------------------------|
| `blslms/logs/django.log`   | Django framework warnings/errors  |
| `blslms/logs/blslms.log`   | App logic (views, utils, emails)  |
| `blslms/logs/celery.log`   | Celery task execution             |

These rotate at 5 MB × 5 backups.

### Systemd journal logs

```bash
# All units
sudo journalctl -u gunicorn -u celery -u celerybeat --since "1 hour ago"

# Specific unit, last 200 lines
sudo journalctl -u celery --no-pager -n 200
```

### nginx logs

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## 6. Deploying code changes

```bash
cd /home/django/NEA_2024_Official-main/blslms

# Pull latest
git pull

# Install any new deps
source /home/django/NEA_2024_Official-main/venv/bin/activate
pip install -r ../requirements.txt

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

deactivate

# Restart services
sudo systemctl restart gunicorn celery celerybeat
```

---

## 7. Environment variables

Located at `/etc/blslms.env` (referenced from systemd units).

Required keys:
```
DJANGO_SECRET_KEY=<long random string>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=elibrary.businesslaw.school
NOREPLY_EMAIL=noreply@businesslaw.school
NOREPLY_PWD=<smtp password>
API_NINJA_KEY=<profanity filter API key>
```

After changing env vars: `sudo systemctl restart gunicorn celery celerybeat`
