import unittest

from backend_ojeda.integration_config import test_database_config


class IntegrationConfigTests(unittest.TestCase):
    def test_siempre_crea_otra_base_con_conexiones_independientes(self):
        config = test_database_config('postgresql://qa:clave%40x@localhost:5433/tuplaza_qa_inventario?sslmode=require')
        self.assertEqual(config['TEST']['NAME'], 'test_tuplaza_qa_inventario')
        self.assertNotEqual(config['NAME'], config['TEST']['NAME'])
        self.assertEqual(config['PASSWORD'], 'clave@x')
        self.assertEqual(config['PORT'], 5433)
        self.assertEqual(config['CONN_MAX_AGE'], 0)
        self.assertEqual(config['OPTIONS']['sslmode'], 'require')

    def test_no_admite_configuracion_ausente_sqlite_ni_nombres_operativos(self):
        for url in (None, '', 'sqlite:///db.sqlite3', 'postgres://host/railway',
                    'postgres://host/production', 'postgres:///tuplaza_qa_demo',
                    'postgres://host/tuplaza_qa_'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                test_database_config(url)

    def test_error_no_expone_credenciales(self):
        with self.assertRaises(ValueError) as caught:
            test_database_config('postgres://usuario:secreto@host:puerto/tuplaza_qa_demo')
        self.assertNotIn('secreto', str(caught.exception))
        self.assertNotIn('usuario', str(caught.exception))

    def test_no_admite_opciones_arbitrarias_de_conexion(self):
        for suffix in ('?options=-csearch_path=public', '?sslmode=invalid',
                       '?sslmode=require&sslmode=disable', '#fragmento'):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                test_database_config('postgres://host/tuplaza_qa_demo' + suffix)
