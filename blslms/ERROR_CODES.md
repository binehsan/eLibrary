# BLS eLibrary — Error Codes Reference

| Code       | HTTP | Meaning                                    |
|------------|------|--------------------------------------------|
| BLS-E001   | 404  | Book not found                             |
| BLS-E002   | 404  | Loan not found                             |
| BLS-E003   | 404  | Penalty not found                          |
| BLS-E004   | 404  | Review not found                           |
| BLS-E005   | 404  | Bookmark not found                         |
| BLS-E006   | 404  | User / profile not found                   |
| BLS-E007   | 403  | Unauthorised access (wrong user)           |
| BLS-E008   | 400  | Invalid form submission                    |
| BLS-E009   | 400  | Page number out of range (bookmark)        |
| BLS-E010   | 409  | No physical copies available (collect)     |
| BLS-E011   | 500  | Internal / unexpected server error         |

## Where to find logs

| Log file                            | What it captures                       |
|-------------------------------------|----------------------------------------|
| `blslms/logs/django.log`           | Django framework warnings & errors     |
| `blslms/logs/blslms.log`           | Application-level logs (views, utils)  |
| `blslms/logs/celery.log`           | Celery task logs                       |

### Systemd journal (Celery / Gunicorn)

```bash
# Celery worker
sudo journalctl -u celery --no-pager -n 100

# Celery beat
sudo journalctl -u celerybeat --no-pager -n 100

# Gunicorn
sudo journalctl -u gunicorn --no-pager -n 100

# Follow live
sudo journalctl -u celery -f
```

### Tail app logs directly

```bash
tail -f /home/django/NEA_2024_Official-main/blslms/logs/blslms.log
tail -f /home/django/NEA_2024_Official-main/blslms/logs/celery.log
tail -f /home/django/NEA_2024_Official-main/blslms/logs/django.log
```
