FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# The key is only needed to load the settings during the build; it is not used at runtime.
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Render passes the port in $PORT; locally the default 8000 is used.
# populate_history --auto gives existing rows without history a starting snapshot (US-12).
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py populate_history --auto && gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2"]
