"""Auditoría de solo lectura. No ejecuta ni escribe migraciones."""
import json

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count, F, Q, Sum
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.state import ProjectState

from backend_ojeda.deployment import deployment_revision
from store.models import InventarioAlmacen, ProductoTienda


class Command(BaseCommand):
    help = 'Informa revisión, migraciones y discrepancias de inventario sin modificar datos.'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=20, help='Máximo de IDs en la muestra (1 a 100).')
        parser.add_argument('--skip-stock', action='store_true', help='Sólo revisar migraciones y revisión.')
        parser.add_argument('--check', action='store_true', help='Salir con error si hay pendientes o discrepancias.')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql' or connection.in_atomic_block:
            raise CommandError('Ejecuta el diagnóstico directamente sobre PostgreSQL, fuera de otra transacción.')
        if not 1 <= options['limit'] <= 100:
            raise CommandError('El límite debe estar entre 1 y 100.')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                cursor.execute("SET LOCAL statement_timeout = '15s'")
            # MigrationLoader lee django_migrations; no llama ensure_schema/migrate.
            loader = MigrationLoader(connection, ignore_no_migrations=True)
            loader.check_consistent_history(connection)
            pendientes = sorted(
                name for app, name in loader.graph.nodes
                if app == 'store' and (app, name) not in loader.applied_migrations
            )
            conflicts = loader.detect_conflicts()
            disk = MigrationLoader(None, ignore_no_migrations=True)
            changes = MigrationAutodetector(
                disk.project_state(), ProjectState.from_apps(apps),
                MigrationQuestioner(specified_apps={'store'}, dry_run=True),
            ).changes(graph=disk.graph, trim_to_apps={'store'}) if not conflicts else {}
            operaciones = [
                {'app': app, 'operacion': operation.__class__.__name__, 'descripcion': operation.describe()}
                for app, migrations in sorted(changes.items())
                for migration in migrations for operation in migration.operations
            ]
            report = {
                'revision': deployment_revision(),
                'solo_lectura': True,
                'migraciones_store_pendientes': pendientes,
                'conflictos_migraciones': conflicts,
                'cambios_modelos_sin_migracion': operaciones,
                'inventario': None,
            }
            problems = bool(pendientes or conflicts or operaciones)
            if not options['skip_stock'] and not pendientes and not conflicts:
                productos = ProductoTienda.objects.filter(
                    tipo=ProductoTienda.TIPO_PRODUCTO, stock__isnull=False,
                ).annotate(total_almacenes=Sum('existencias_almacen__cantidad'),
                           filas=Count('existencias_almacen'))
                diferencias = productos.filter(filas__gt=0).exclude(stock=F('total_almacenes'))
                ajenas = InventarioAlmacen.objects.exclude(
                    producto__tienda_id=F('almacen__sucursal__negocio__tienda_id'),
                )
                sin_control = InventarioAlmacen.objects.filter(
                    Q(producto__tipo=ProductoTienda.TIPO_SERVICIO) | Q(producto__stock__isnull=True),
                )
                report['inventario'] = {
                    'productos_con_total_inconsistente': diferencias.count(),
                    'muestra_totales': list(diferencias.order_by('pk').values(
                        'id', 'stock', 'total_almacenes')[:options['limit']]),
                    'existencias_de_otro_negocio': ajenas.count(),
                    'muestra_existencias_ajenas': list(ajenas.order_by('pk').values_list(
                        'pk', flat=True)[:options['limit']]),
                    'filas_de_servicios_o_productos_sin_control': sin_control.count(),
                    # Informativo: un producto legado puede no tener detalle todavía.
                    'productos_controlados_sin_detalle': productos.filter(filas=0).count(),
                }
                audit = report['inventario']
                problems = problems or any(audit[key] for key in (
                    'productos_con_total_inconsistente', 'existencias_de_otro_negocio',
                    'filas_de_servicios_o_productos_sin_control',
                ))
            report['requiere_revision'] = bool(problems)
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        if options['check'] and problems:
            raise CommandError('El diagnóstico encontró pendientes; revisa el informe antes de migrar.')
