# Backend image: Django + DRF + GeoDjango
FROM python:3.13-slim

# Don't write .pyc files; flush logs straight to `docker logs`
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# GeoDjango needs the GDAL, GEOS, and PROJ system libraries.
# gdal-bin pulls in all three.
RUN apt-get update \
    && apt-get install -y --no-install-recommends binutils libproj-dev gdal-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages first so this layer is cached between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect admin static files at build time (needs no database)
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
# Production default; docker-compose.yml overrides this with runserver for dev
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
