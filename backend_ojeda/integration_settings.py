"""Sólo para el runner de integración en un entorno preparado (no para deploy)."""
import os

from .integration_config import test_database_config

# Validar antes de cargar la configuración habitual: no hay fallback a DATABASE_URL.
_test_database = test_database_config(os.environ.get('TUPLAZA_TEST_DATABASE_URL'))

from .settings import *  # noqa: E402,F403

DATABASES = {'default': _test_database}
SECRET_KEY = 'tuplaza-only-for-isolated-integration-tests'
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
SECURE_SSL_REDIRECT = False
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EXPO_PUSH_DISABLED = True
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_THROTTLE_CLASSES': []}  # noqa: F405
