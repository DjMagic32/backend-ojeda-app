import os
import unittest
from unittest.mock import patch

from backend_ojeda.deployment import deployment_revision


class DeploymentRevisionTests(unittest.TestCase):
    def test_revision_valida(self):
        with patch.dict(os.environ, {'RAILWAY_GIT_COMMIT_SHA': 'A' * 40}):
            self.assertEqual(deployment_revision(), 'a' * 40)

    def test_variable_ausente_no_inventa_revision(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(deployment_revision())

    def test_no_publica_contenido_arbitrario(self):
        for value in ('secreto', 'https://usuario:clave@host', 'abcdef', 'a' * 41):
            with self.subTest(value=value), patch.dict(os.environ, {'RAILWAY_GIT_COMMIT_SHA': value}):
                self.assertIsNone(deployment_revision())
