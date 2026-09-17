FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Instalar las dependencias del proyecto
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/

# Crear las carpetas usadas por Django
RUN mkdir -p /code/static /code/media

CMD ["sh", "/code/start.sh"]
