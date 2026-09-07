FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps:
#   qpdf          - pikepdf (protect / unlock)
#   ghostscript   - compression
#   libreoffice   - DOCX <-> PDF conversion. The full package (not just
#                   -writer) is required: the PDF -> DOCX fallback uses the
#                   writer_pdf_import filter, which ships with libreoffice-draw.
# poppler-utils is gone: PDF rendering now goes through PyMuPDF, no binary needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    qpdf \
    ghostscript \
    libreoffice \
    fonts-liberation \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps before copying source, for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic needs a non-empty SECRET_KEY; the real one is injected at runtime.
RUN DJANGO_SECRET_KEY=build-only-placeholder \
    ALLOWED_HOSTS=* \
    DEBUG=false \
    python manage.py collectstatic --noinput

# Run as an unprivileged user. The code in /app stays root-owned and read-only;
# only these two directories are writable:
#   media/ - files being converted
#   data/  - the SQLite fallback, used when DATABASE_URL is unset. It cannot
#            live beside the code, because /app is not writable by this user.
ENV SQLITE_PATH=/app/data/db.sqlite3
RUN mkdir -p /app/media /app/data \
    && useradd --system --uid 1000 --home /app pdfix \
    && chown -R pdfix:pdfix /app/media /app/data
USER pdfix

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",8000)}/healthz', timeout=4).status==200 else 1)"

# --timeout must exceed the conversion budget in tools/services/pdf_to_docx.py,
# or gunicorn kills the worker mid-job and the user gets a 502 instead of an error.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --threads 2 --timeout 300 --no-control-socket --graceful-timeout 30 --max-requests 200 --max-requests-jitter 50 --access-logfile - --error-logfile -"]
