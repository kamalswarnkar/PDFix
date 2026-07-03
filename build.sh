#!/usr/bin/env bash
# Build script for Render (and similar PaaS that run a build command).
# This runs at build time — do NOT start the server here.
# ponytail: gunicorn is the runtime start command (Procfile / Dockerfile CMD), not build.
set -euo pipefail

pip install --no-cache-dir -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput