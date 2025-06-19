FROM python:3.12-slim

# Evita archivos .pyc y fuerza logs sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Instalar las dependencias del proyecto
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/

# Copia el entrypoint y dale permisos
COPY entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh

# Expone el puerto que usará Gunicorn o runserver
EXPOSE 8000

# ¡Aquí la magia!  👇
ENTRYPOINT ["/code/entrypoint.sh"]

# Crear la carpeta estática (si no existe)
RUN mkdir -p /code/static

# Realizar las migraciones y el collectstatic automáticamente al iniciar
CMD python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000

# python manage.py makemigrations store && python manage.py makemigrations && python manage.py migrate &&