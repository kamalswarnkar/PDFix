#!/usr/bin/env bash

pip install -r requirements.txt

apt-get update
apt-get install -y poppler-utils ghostscript libreoffice

python manage.py collectstatic --noinput
python manage.py migrate