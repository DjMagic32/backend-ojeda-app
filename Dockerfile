FROM python:3.12-slim

WORKDIR /code

# Instalar las dependencias del proyecto
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/

# Crear la carpeta estática (si no existe)
RUN mkdir -p /code/static

# Realizar las migraciones y el collectstatic automáticamente al iniciar
CMD python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000

# python manage.py makemigrations store && python manage.py makemigrations && python manage.py migrate &&