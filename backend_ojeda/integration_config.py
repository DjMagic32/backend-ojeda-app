"""Configuración de PostgreSQL desechable, sin importar Django ni leer .env."""
import re
from urllib.parse import parse_qs, unquote, urlsplit


def test_database_config(url):
    message = ('Configura TUPLAZA_TEST_DATABASE_URL con PostgreSQL de pruebas y una '
               'base llamada tuplaza_qa_<nombre>. No uses la URL de producción.')
    try:
        parsed = urlsplit(url or '')
        name = unquote(parsed.path.lstrip('/'))
        if (parsed.scheme not in {'postgres', 'postgresql'} or not parsed.hostname
                or not re.fullmatch(r'tuplaza_qa_[a-z0-9_]{1,32}', name)
                or parsed.fragment):
            raise ValueError(message)
        query = parse_qs(parsed.query, keep_blank_values=True)
        if set(query) - {'sslmode'}:
            raise ValueError(message)
        sslmode = query.get('sslmode', ['prefer'])
        if len(sslmode) != 1 or sslmode[0] not in {
            'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full',
        }:
            raise ValueError(message)
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': name,
            'USER': unquote(parsed.username or ''),
            'PASSWORD': unquote(parsed.password or ''),
            'HOST': parsed.hostname,
            'PORT': parsed.port or 5432,
            'CONN_MAX_AGE': 0,
            'OPTIONS': {
                'sslmode': sslmode[0], 'connect_timeout': 10,
                'options': '-c statement_timeout=15000 -c lock_timeout=8000',
            },
            # El runner crea y destruye esta base; nunca reutiliza NAME.
            'TEST': {'NAME': f'test_{name}'},
        }
    except (ValueError, TypeError) as exc:
        # No incluir URLs, usuarios ni contraseñas en errores.
        raise ValueError(message) from None
