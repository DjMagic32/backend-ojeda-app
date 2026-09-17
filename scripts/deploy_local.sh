#!/usr/bin/env bash
set -Eeuo pipefail

# El runner puede ejecutarse desde cualquier directorio, pero Docker debe usar
# siempre este checkout y sus carpetas persistentes de static/media.
DEPLOY_DIR="${DEPLOY_DIR:-/Users/davidgarcia/Documents/work/projet-ojeda/backend-ojeda-app}"
BRANCH="${DEPLOY_BRANCH:-dev}"
COMPOSE_FILE="docker-compose.production.yml"
LOCK_DIR="/tmp/backend-ojeda-deploy.lock"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Ya hay un despliegue en ejecución: $LOCK_DIR" >&2
  exit 1
fi
trap 'rmdir "$LOCK_DIR"' EXIT

cd "$DEPLOY_DIR"

if [[ "$(git branch --show-current)" != "$BRANCH" ]]; then
  echo "El checkout no está en la rama $BRANCH; se cancela el despliegue." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "El checkout tiene cambios locales; se cancela el despliegue." >&2
  exit 1
fi

echo "Actualizando $BRANCH..."
git fetch origin "$BRANCH"
git merge --ff-only "origin/$BRANCH"

echo "Construyendo y levantando Docker..."
# No usar down -v: el volumen postgres_data contiene la base de datos.
docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans

echo "Comprobando migraciones..."
# start.sh ya aplica las migraciones al arrancar. --check confirma que no
# quedó ninguna pendiente y no modifica ni borra la base de datos.
for attempt in $(seq 1 30); do
  if docker compose -f "$COMPOSE_FILE" exec -T web python manage.py migrate --check; then
    break
  fi
  if [[ "$attempt" == 30 ]]; then
    echo "No se pudieron comprobar las migraciones después de 60 segundos." >&2
    exit 1
  fi
  sleep 2
done

echo "Despliegue terminado: $(git rev-parse --short HEAD)"
