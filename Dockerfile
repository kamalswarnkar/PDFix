FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps: Poppler (pdf2image), QPDF (pikepdf), Ghostscript (compress),
# LibreOffice + fonts (DOCX↔PDF conversion)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    qpdf \
    ghostscript \
    libreoffice \
    fonts-liberation \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps before copying source for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic needs a non-empty SECRET_KEY; the real one is injected at runtime
RUN DJANGO_SECRET_KEY=build-only-placeholder \
    ALLOWED_HOSTS=* \
    DEBUG=false \
    python manage.py collectstatic --noinput

# Pre-create media dir so the volume mount target exists in the image
RUN mkdir -p /app/media

EXPOSE 8000

# migrate first (idempotent), then serve
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
