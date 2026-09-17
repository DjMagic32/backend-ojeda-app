"""Compara la migración escrita con los modelos nuevos sin ejecutar Django."""
import ast
from pathlib import Path
import unittest


class CajaMigrationTests(unittest.TestCase):
    def test_solo_crea_modelos_nuevos_con_campos_y_restricciones_equivalentes(self):
        root = Path(__file__).resolve().parents[1]
        model_tree = ast.parse((root / 'store/models.py').read_text())
        migration_tree = ast.parse((root / 'store/migrations/0041_sesiones_caja.py').read_text())
        names = {'MONEDA_USD': 'USD', 'MONEDA_VES': 'VES', 'SesionCaja': 'store.sesioncaja'}

        def value(node):
            if isinstance(node, ast.Constant): return node.value
            if isinstance(node, ast.Name): return names[node.id]
            if isinstance(node, ast.Attribute): return node.attr
            if isinstance(node, (ast.List, ast.Tuple)): return tuple(value(item) for item in node.elts)
            if isinstance(node, ast.Dict): return {value(k): value(v) for k, v in zip(node.keys, node.values)}
            if isinstance(node, ast.Call):
                kwargs = {k.arg: value(k.value) for k in node.keywords}
                if node.args:
                    self.assertEqual(node.func.attr, 'ForeignKey')
                    kwargs['to'] = value(node.args[0])
                return node.func.attr, kwargs
            raise AssertionError(ast.dump(node))

        for node in model_tree.body:
            if isinstance(node, ast.Assign) and node.targets[0].id == 'MONEDAS':
                names['MONEDAS'] = value(node.value)
        classes = {n.name: n for n in model_tree.body if isinstance(n, ast.ClassDef)}
        migration = next(n for n in migration_tree.body if isinstance(n, ast.ClassDef))
        attrs = {n.targets[0].id: n.value for n in migration.body if isinstance(n, ast.Assign)}
        self.assertEqual(value(attrs['dependencies']), (('store', '0040_operacion_venta_presencial'),))
        self.assertEqual(len(attrs['operations'].elts), 3)
        for operation in attrs['operations'].elts:
            self.assertEqual(operation.func.attr, 'CreateModel')
            parameters = {k.arg: k.value for k in operation.keywords}
            name = value(parameters['name'])
            self.assertIn(name, ('SesionCaja', 'MovimientoCaja', 'OperacionCaja'))
            fields = {}
            options = {}
            for node in classes[name].body:
                if isinstance(node, ast.Assign):
                    if isinstance(node.value, ast.Call): fields[node.targets[0].id] = value(node.value)
                    else: names[node.targets[0].id] = value(node.value)
                if isinstance(node, ast.ClassDef) and node.name == 'Meta':
                    options = {a.targets[0].id: value(a.value) for a in node.body if isinstance(a, ast.Assign)}
            migrated_fields = dict(value(parameters['fields']))
            migrated_fields.pop('id')
            self.assertEqual(fields, migrated_fields, name)
            self.assertEqual(options, value(parameters['options']), name)
