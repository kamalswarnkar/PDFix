#!/usr/bin/env bash
set -e

pip install -r requirements.txt

apt-get update
apt-get install -y --no-install-recommends poppler-utils ghostscript libreoffice

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# ponytail: WSGI module is config.wsgi (Django project name), not PDFix.wsgi
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120