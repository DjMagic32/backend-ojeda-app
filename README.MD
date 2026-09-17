Aquí tienes un ejemplo de cómo podría quedar tu archivo `README.md` con las instrucciones para arrancar el proyecto y realizar las migraciones en el entorno de Docker Compose.

---

# Proyecto Django con Docker

Este proyecto es una aplicación Django que utiliza Docker y Docker Compose para gestionar el entorno de desarrollo. Este archivo contiene las instrucciones para arrancar el proyecto, realizar las migraciones y otros pasos necesarios.

## Requisitos previos

Antes de comenzar, asegúrate de tener las siguientes herramientas instaladas en tu máquina:

- Docker: [Descargar Docker](https://www.docker.com/products/docker-desktop)
- Docker Compose: [Descargar Docker Compose](https://docs.docker.com/compose/install/)

## Pasos para arrancar el proyecto

1. **Clonar el repositorio:**

   Clona este repositorio en tu máquina local:

   ```bash
   git clone https://github.com/tu-usuario/tu-repositorio.git
   cd tu-repositorio
   ```

2. **Construir las imágenes de Docker:**

   Primero, debes construir las imágenes necesarias para los servicios `web` y `db` (el contenedor de la base de datos). Ejecuta el siguiente comando:

   ```bash
   docker-compose build
   ```

3. **Levantar los contenedores:**

   Una vez que las imágenes se hayan construido, puedes levantar los contenedores de Docker con el siguiente comando:

   ```bash
   docker-compose up -d
   docker compose up -d
   docker compose ps
   docker compose logs -f web
   ```

   Este comando arrancará los contenedores en segundo plano (`-d` significa "detached"). Puedes verificar que están corriendo con:

   ```bash
   docker-compose ps
   ```

4. **Realizar las migraciones:**

   Para realizar las migraciones de la base de datos y asegurarte de que todo esté actualizado, debes ejecutar los siguientes comandos dentro del contenedor `web`:

   ```bash
   docker-compose exec web python manage.py migrate
   ```

   Este comando aplicará todas las migraciones de tu proyecto y actualizará la base de datos según el esquema definido en tus modelos de Django.

5. **Cargar los archivos estáticos:**

   Si tienes archivos estáticos que necesitas recopilar (por ejemplo, archivos CSS, imágenes, etc.), puedes hacerlo con el siguiente comando:

   ```bash
   docker-compose exec web python manage.py collectstatic --noinput
   ```

   Este comando recopilará todos los archivos estáticos y los almacenará en el contenedor para servirlos.

6. **Acceder a la aplicación:**

   Ahora, puedes acceder a la aplicación Django en tu navegador. El servidor estará disponible en `http://localhost:8000`.

   ¡Listo! Ya tienes tu proyecto Django corriendo en Docker.

## Pasos adicionales

### Detener los contenedores

Si deseas detener los contenedores y liberar los recursos que están utilizando, puedes hacerlo con:

```bash
docker-compose down
```

### Eliminar los volúmenes y contenedores

Si necesitas eliminar todos los contenedores, imágenes, y volúmenes asociados al proyecto, puedes ejecutar:

```bash
docker-compose down --volumes --rmi all
```

Este comando eliminará todos los volúmenes persistentes y las imágenes construidas.

## Solución de problemas

Si te encuentras con problemas comunes como "el contenedor de la base de datos no arranca" o "no se pueden aplicar las migraciones", verifica los siguientes puntos:

- Asegúrate de que la base de datos está corriendo correctamente. Puedes verificar el estado del contenedor de la base de datos con `docker-compose ps`.
- Verifica que las variables de entorno en el archivo `.env` estén correctamente configuradas.
- Si es necesario, elimina los contenedores y volúmenes existentes y vuelve a construir las imágenes y levantarlas.

---

Este `README.md` proporciona una guía completa para arrancar el proyecto desde cero y realizar las migraciones correctamente. Puedes ajustar cualquier sección dependiendo de la configuración de tu proyecto o si tienes pasos adicionales que realizar.

## Configuración mínima de producción

### Despliegue automático en la Mac mediante GitHub Actions

Producción corre en la Mac mediante `docker-compose.production.yml`. El workflow
`.github/workflows/deploy-local.yml` se dispara al hacer push a `dev` y usa un
runner de GitHub instalado en esta misma máquina. El script de despliegue hace
`fetch`/`fast-forward`, reconstruye Docker y comprueba las migraciones.

El despliegue nunca ejecuta `docker compose down --volumes` ni elimina el
volumen `postgres_data`. Las migraciones se aplican desde `start.sh` y luego se
verifican con `migrate --check`.

La producción local también incluye Redis para WebSockets (Django Channels),
caché y límites de solicitudes. Su volumen es `redis_data`. Las imágenes y
archivos adjuntos pueden mantenerse en la carpeta persistente `./media` o
configurarse en un bucket compatible con S3/R2 usando las variables de
`.env.production.example`. Para enviar correos hay que configurar `RESEND_API_KEY`
o las variables SMTP; sin ellas Django solo los imprime en los logs.

Para activar el workflow una sola vez:

1. En GitHub: `Settings > Actions > Runners > New self-hosted runner`.
2. Seleccionar macOS y ejecutar en la Mac los comandos de instalación que
   GitHub proporciona.
3. Añadir la etiqueta personalizada `ojeda` y dejar el runner ejecutándose.
4. Asegurarse de que el usuario del runner tenga acceso a Docker Desktop y al
   checkout indicado en `scripts/deploy_local.sh`.

Después, cada push a `dev` actualizará esta Mac automáticamente. Si el runner
está detenido, GitHub conservará el job pendiente hasta que vuelva a estar
disponible.

En la Mac configura estas variables en `.env.production` antes de desplegar:

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<clave-larga-aleatoria-y-privada>
DJANGO_ALLOWED_HOSTS=<dominio-publico>
DJANGO_SERVE_API_DOCS=False
DJANGO_SECURE_SSL_REDIRECT=True
REDIS_URL=<url-del-servicio-redis>
```

`DJANGO_SECRET_KEY` no debe reutilizarse entre entornos ni subirse al
repositorio. Si falta en producción, el backend ahora detiene el arranque.
La documentación interactiva queda cerrada fuera de desarrollo y los límites
de solicitudes usan Redis cuando `REDIS_URL` está disponible.
