import os
import re


def deployment_revision():
    """Sólo publicar un SHA válido; nunca volcar variables del despliegue."""
    revision = os.environ.get('RAILWAY_GIT_COMMIT_SHA', '').strip().lower()
    return revision if re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', revision) else None
