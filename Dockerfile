# Usa una imagen base oficial de Alpine Linux
FROM alpine:3.14

# Instala Python 3.12.8 y bash
RUN apk add --no-cache python3=3.12.8-r0 python3-dev=3.12.8-r0 bash

# Establece el directorio de trabajo
WORKDIR /code

# Copia los archivos de requerimientos y los instala
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código de la aplicación
COPY . /code/

# Expone el puerto 8000 (o el puerto en el que tu aplicación está configurada para correr)
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
