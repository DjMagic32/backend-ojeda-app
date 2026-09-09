# Plan de pruebas: módulo de negocios de TuPlaza

Checklist para ejecutar después de implementar cada bloque del documento
`fina-partner-gap-checklist.md`. La prueba no se considera completa si sólo funciona el
endpoint: también debe validarse la app, los permisos, la migración y la regresión de los
flujos actuales.

## Convenciones

- `[x]` Verificado.
- `[~]` Verificado parcialmente o con una limitación conocida.
- `[ ]` Pendiente.
- `API` significa prueba contra REST/GraphQL; `App` significa prueba en Android; `Ops`
  significa migración, despliegue y observabilidad.

## Datos de prueba mínimos

- `[ ]` Usuario cliente sin tienda.
- `[ ]` Propietario de una tienda con productos, servicios, órdenes y pagos.
- `[ ]` Usuario administrador invitado a una tienda.
- `[ ]` Usuario de otra tienda para comprobar aislamiento.
- `[ ]` Producto con stock, producto sin stock y servicio.
- `[ ]` Dos sucursales y dos almacenes con existencias diferentes.
- `[ ]` Una orden online, una venta presencial, un pago en USD y uno en VES.
- `[ ]` Conectividad normal, red lenta, desconexión y reconexión.

## Smoke test actual antes de cada APK

### Autenticación y sesión

- `[ ]` Registrar cliente, tienda y conductor.
- `[ ]` Iniciar sesión, cerrar y volver a abrir la app.
- `[ ]` Confirmar que el refresh de sesión no expulsa al usuario sin motivo.
- `[ ]` Recuperar contraseña con código correcto, incorrecto y vencido.
- `[ ]` Cerrar sesión manualmente y confirmar que los datos protegidos se limpian.

### Marketplace

- `[ ]` Ver productos, servicios, comidas y artículos de segunda mano.
- `[ ]` Abrir detalle, reseñas, perfil de tienda y reputación.
- `[ ]` Agregar/quitar favorito y comprobar actualización al regresar con `back`.
- `[ ]` Agregar al carrito, modificar cantidad y crear una orden.
- `[ ]` Confirmar que un usuario común puede publicar artículos sin crear una tienda.

### Pedidos y delivery

- `[ ]` Crear servicio de taxi, delivery y encomienda.
- `[ ]` Confirmar que las solicitudes y cambios de estado llegan por WebSocket.
- `[ ]` Verificar que cliente, tienda y conductor ven sólo la información que les
  corresponde.
- `[ ]` Confirmar que una orden completada o cancelada no puede retroceder de estado.
- `[ ]` Abrir el seguimiento desde `Mis pedidos` después de salir de la pantalla.

### Chat y notificaciones

- `[ ]` Enviar texto, imagen, PDF, comprobante de pago y ubicación.
- `[ ]` Abrir imagen dentro de la app, hacer zoom y descargarla.
- `[ ]` Copiar códigos desde el chat.
- `[ ]` Confirmar badge en tiempo real y que el badge se limpia al abrir la conversación.
- `[ ]` Confirmar que no se emite push mientras el usuario ya está dentro del chat.
- `[ ]` Probar notificación nativa con app abierta, en segundo plano y cerrada.

## Pruebas del primer bloque: Negocio y ubicación

### Migración y creación automática

- `[ ]` Ejecutar `python manage.py migrate` en una base de datos de prueba.
- `[ ]` Confirmar que cada tienda existente recibe exactamente un `Negocio`.
- `[ ]` Confirmar que cada negocio recibe exactamente un miembro `owner`.
- `[ ]` Confirmar que cada negocio recibe una sucursal `PRINCIPAL` y un almacén
  `PRINCIPAL`.
- `[ ]` Registrar una tienda nueva por REST y confirmar la creación automática de las
  cuatro relaciones esperadas.
- `[ ]` Registrar/completar una tienda nueva por GraphQL y confirmar el mismo resultado.
- `[ ]` Ejecutar la migración dos veces y verificar que no duplica datos.
- `[ ]` Comprobar que una dirección vacía no impide crear la estructura principal.

### Endpoint `GET /api/store/mi-negocio/`

- `[ ]` El propietario recibe su negocio, miembros y sucursales.
- `[ ]` Un miembro activo recibe el mismo negocio.
- `[ ]` Un usuario cliente sin relación recibe `404` sin filtrar información.
- `[ ]` Un miembro inactivo deja de tener acceso.
- `[ ]` La respuesta no incluye contraseñas, tokens, información de cobro ni datos
  innecesarios de otros usuarios.
- `[ ]` La respuesta contiene almacenes anidados y códigos únicos.
- `[ ]` Un negocio inactivo no se presenta como operativo cuando se implemente esa regla.

### App

- `[ ]` El perfil de una tienda propia muestra “Negocio activo”.
- `[ ]` Muestra la cantidad correcta de miembros, sucursales y almacenes activos.
- `[ ]` Un perfil público de otra tienda no muestra el contexto administrativo.
- `[ ]` Con un backend anterior a la migración, el perfil sigue mostrando catálogo y no se
  cae la pantalla.
- `[ ]` Con respuesta lenta, aparece el estado de carga sin bloquear el resto del perfil.
- `[ ]` Al volver al perfil, los datos se vuelven a cargar sin duplicar componentes.

### Estado de implementación del segundo bloque

- **API:** `[x]` CRUD protegido de sucursales y almacenes, sin eliminación física.
- **App:** `[x]` pantalla de alta y desactivación accesible desde el perfil de la tienda.
- **Operación:** `[x]` la migración `0037_sucursal_almacen` se ejecutó en Railway sin
  migraciones pendientes; falta validar los datos reales con usuarios de prueba.
- **Pendiente funcional:** `[~]` la asociación inicial y la transferencia básica ya están
  implementadas; queda probarlas y completar recepción/controles avanzados.

### Renombrado de sucursales y almacenes (2026-09-09)

Implementado en `BusinessLocations`, accesible desde perfil de tienda → Sucursales →
Editar nombre. Consume `PATCH /api/store/sucursales/{id}/` y
`PATCH /api/store/almacenes/{id}/` con sólo `nombre`. No requiere migraciones.

- `[x]` `python3 -m py_compile store/models.py store/serializers.py store/views.py store/urls.py`.
- `[x]` `npx tsc --noEmit`: salida idéntica antes/después, 75 errores preexistentes,
  ninguno nuevo en la pantalla modificada.
- `[x]` Smoke de Railway: salud `200`, siete rutas administrativas `401` y ambos PATCH
  con ID `0` y sin credenciales devuelven `401`. No acredita un guardado autenticado.
- `[ ]` Android: renombrar una sucursal y un almacén; salir y volver a entrar para confirmar
  persistencia. Comprobar también registros inactivos y nombres largos.
- `[ ]` Cancelar y cerrar con Atrás sin guardar; el nombre debe conservarse.
- `[ ]` Nombre vacío o sólo espacios no permite guardar; máximo 120 caracteres. Un error
  de red o validación mantiene el formulario y permite reintentar; doble toque no duplica
  solicitudes mientras se guarda.
- `[ ]` Confirmar que códigos (incluido `PRINCIPAL`), estado activo, relaciones y saldos
  siguen iguales; volver a caja, ajustes y transferencias y comprobar el nuevo nombre.
- `[ ]` Verificar rechazo de PATCH autenticado sobre IDs de otro negocio.

Estas comprobaciones funcionales quedan registradas para la validación del bloque;
no son un requisito para continuar implementando los siguientes pendientes del checklist.

### Estado de implementación del tercer bloque: inventario y transferencias

- **API:** `[~]` modelo `InventarioAlmacen`, migraciones `0038_inventario_almacen` y
  `0039_transferencia_inventario`, consulta protegida y transferencia atómica entre
  almacenes con movimientos de salida/entrada trazables.
- **App:** `[~]` resumen de productos asociados por almacén, historial con ubicación del
  movimiento y pantalla para transferir existencias; selección de almacén en ventas/ajustes
  implementada. Queda validarla en Android y completar recepción avanzada.
- **Operación:** `[x]` `0038_inventario_almacen` y `0039_transferencia_inventario` se
  ejecutaron en Railway y respondieron `No migrations to apply`.
- **Pruebas:** `[ ]` ejecutar los casos de inventario con dos almacenes, transferencia
  insuficiente, concurrencia, servicios sin stock y compatibilidad con clientes antiguos.

## Evidencia del quinto bloque: ajustes y transferencias (2026-09-09)

Bases revisadas: backend `cb7bb86` y frontend `151fd8e`, ambos en `dev`, limpios y
sincronizados con `origin/dev` antes de editar. Sin cambios de modelos ni nuevas migraciones.

- `[x]` `python3 -m py_compile store/services/inventario.py store/views.py
  tests/test_inventario_service.py scripts/smoke_inventory_routes.py`.
- `[x]` `python3 -m unittest discover -s tests -v`: 17 pruebas del servicio real con dobles
  de ORM. Cubren conteos por almacén, deltas, fallback principal/legado, conteo sin cambios,
  activación en cero, servicios, insuficiencia, almacenes ajenos/inactivos y transferencias.
  **No son pruebas de Django ni acreditan transacciones SQL, rollback o concurrencia.**
- `[x]` La regresión de transferencia con stock sólo en un tercer almacén falla sobre
  `cb7bb86` (`ValidationError not raised`) y pasa con la corrección.
- `[x]` Frontend: `node --test scripts/inventory.test.cjs`, 7 pruebas del helper real:
  saldos diferentes, almacén sin fila, carga fallida, cero, ausencia de control y fallback.
- `[x]` Frontend: `npx tsc --noEmit`, 75 errores preexistentes; salida idéntica antes/después
  y sin nuevos errores en archivos modificados. No equivale a typecheck global limpio.
- `[x]` `python3 scripts/smoke_inventory_routes.py
  https://backend-ojeda-app-production.up.railway.app`: salud `200`; `401` para GET de
  negocio, inventario, transferencias y movimientos, y POST de ajuste, transferencia y venta.
  No usa credenciales ni modifica datos; no acredita el comportamiento autenticado.
- `[~]` Aviso de migraciones revisado en código: falta `transferencia` en las opciones
  históricas de `MovimientoStock.origen`. Comparación completa pendiente en un entorno
  preparado. `start.sh` condiciona `migrate` a `AUTO_MIGRATE=1`.
- `[ ]` Confirmar en Railway la revisión desplegada y revisar logs del 502 anterior.
- `[ ]` Ejecutar casos autenticados, rollback y concurrencia sobre PostgreSQL de prueba.
- `[ ]` Probar Android y registrar APK, cuentas de prueba y capturas sanitizadas.

### Casos reproducibles pendientes en API y Android

Usar datos de prueba identificados y autorizados: propietario A, propietario B, producto P
con 10 unidades en almacén A1 (principal) y 20 en A2, un almacén A3 vacío, un servicio y
un producto sin control. No ejecutar ajustes sobre inventario operativo para probar.

1. `[ ]` En “Mis productos”, seleccionar A1: saldo 10, total 30. Pulsar `+`: A1=11,
   A2=20, total=31 y un movimiento `+1`. Pulsar `−`: vuelve a 10/20/30. Cambiar a A2:
   muestra 20. Un doble toque mientras hay petición pendiente sólo envía una solicitud.
2. `[ ]` `POST /api/store/productos-tienda/{P}/ajustar-stock/` con
   `{"almacen_id": A1, "nuevo_stock": 11}`: A1=11, A2=20, total=31. Repetir devuelve
   `movimiento: null`. Restablecer la fixture; enviar `{"nuevo_stock": 11}` sin almacén
   produce el mismo conteo en principal. Los botones nuevos deben enviar `delta`, no un
   total calculado por la app.
3. `[ ]` Con saldo A1=10, enviar `delta: -11`: `400`, sin cambiar total ni movimientos.
   Servicio con ajuste: `400`. Producto sin control con `delta`: `400`; con
   `nuevo_stock: 0`: activa el control y registra entrada cero. Provocar un fallo durante
   el movimiento en entorno de prueba: también debe revertirse la activación.
4. `[ ]` Almacén inactivo o de B: ajuste/venta/transferencia rechazados sin cambios.
   Sin principal activo pero con detalle existente, una operación sin `almacen_id` debe
   pedir seleccionar almacén y no modificar sólo el agregado. Probar aparte instalación
   legada sin almacenes/detalle: conserva el ajuste del stock total.
5. `[ ]` Crear fixture con stock sólo en A3 y **sin filas** de inventario para P en A1/A2.
   Transferir A1→A2 debe fallar sin duplicar las unidades de A3 ni dejar filas por rollback.
   Transferir A3→A1 debe conservar el total y generar dos movimientos opuestos.
   En la app, cantidades `1.5` o `2abc` deben rechazarse, no convertirse en 1 o 2.
6. `[ ]` Desconectar al consultar inventario: no mostrar cero ni permitir ajustar el almacén
   sin saldo confirmado; reintentar y recuperar el saldo. Cambiar rápidamente de almacén y
   volver desde transferencias: no mostrar existencias del almacén anterior.
7. `[ ]` En PostgreSQL, enviar deltas simultáneos `+1/+1` desde dos sesiones: ambos deben
   acumularse. Con una unidad, competir venta/ajuste negativo: sólo una salida debe
   confirmar. Validar atomicidad de venta con varias líneas y dos transferencias opuestas.
8. `[ ]` En Modo caja, vender en A2, verificar salida sólo de A2, total y movimiento;
   repetir con servicios, stock insuficiente y clientes antiguos sin almacén explícito.

Las reservas siguen desactivadas y la idempotencia de reintentos de red sigue pendiente.
No marcar las casillas generales de inventario/POS como completas con esta evidencia local.

## Evidencia del sexto bloque: disponibilidad en POS (2026-09-09)

Bases: backend `c7f4fff`, frontend `3dcfcbf`, repositorios limpios y sincronizados con
`origin/dev` al comenzar. Se conserva el aviso de migraciones previamente documentado;
este bloque no añade campos, tablas ni dependencias.

- `[x]` `python3 -m py_compile store/services/ventas.py store/views.py
  tests/test_ventas_service.py`.
- `[x]` `python3 -m unittest discover -s tests -v`: 27 pruebas aprobadas. Las 10 nuevas
  prueban el servicio real con dobles de ORM: productos/almacén por tienda, orden de bloqueo,
  monedas, totales, tasa ausente, líneas repetidas, movimientos y propagación del error
  hacia la transacción. **No prueban rollback SQL ni concurrencia real.**
- `[x]` `node --test scripts/inventory.test.cjs`: 12 pruebas aprobadas. Nuevos casos:
  servicios con stock legado, saldo desconocido, cantidades por almacén, cambio de almacén,
  reconsulta que detecta otra salida y origen vacío con existencias en otra ubicación.
- `[x]` `npx tsc --noEmit`: mismos 75 errores preexistentes; salida final idéntica a la
  línea base, sin errores nuevos en archivos modificados.
- `[x]` `python3 scripts/smoke_inventory_routes.py
  https://backend-ojeda-app-production.up.railway.app`: ocho casos aprobados (salud y
  rechazo anónimo). No se usaron cuentas ni inventario operativo.
- `[ ]` Confirmar revisión desplegada en Railway y ejecutar los casos siguientes.

### Casos autenticados y visuales pendientes

1. `[ ]` Producto P con A1=2, A2=8, total=10. En Modo caja, seleccionar A1, escanear P dos
   veces y comprobar que un tercer escaneo o `+` se rechaza. Debe indicar disponible=2.
2. `[ ]` Cambiar a A2: permitir tres unidades. Volver a A1 conservando el ticket: indicar
   insuficiencia y deshabilitar Cobrar. Reducir a dos: permitir cobrar y confirmar sólo
   salida A1=0; A2 queda en 8.
3. `[ ]` Otra sesión consume stock después de preparar el ticket: al cobrar, la reconsulta
   detecta insuficiencia y no envía la venta. Si la salida compite después de la consulta,
   el backend debe rechazar atómicamente el ticket y conservar sus datos en la app.
4. `[ ]` Pulsar Cobrar dos veces antes del siguiente render: una sola petición desde esa
   pantalla. Mientras cobra no debe aceptar escaneos, cambios de cantidad, eliminación de
   líneas ni cambio de almacén. Esto no acredita reintentos después de un timeout.
5. `[ ]` Consulta fallida o que excede 15 segundos: indicar existencias sin confirmar,
   conservar el ticket y ofrecer actualización; impedir cobro de productos controlados en
   almacén explícito. Servicio con stock legado 0 y producto sin control: no limitar la
   cantidad por existencias. Backend anterior sin contexto administrativo: conserva fallback.
6. `[ ]` Crear producto rápido con stock 1 estando en A2: consultar su inventario antes de
   agregarlo; si está sólo en principal A1, rechazar la adición en A2. Seleccionar A1 y
   escanear permite agregarlo. Probar alta rápida normal estando en A1.
7. `[ ]` Transferencias muestra A1=2; solicitar tres unidades debe rechazarse antes de POST.
   Elegir A2 permite tres y refresca las existencias después. Si falla la consulta, el saldo
   desconocido no debe convertirse en cero ni habilitar Confirmar; recuperar con Actualizar.
8. `[ ]` Navegar entre ajustes, caja y transferencias y cambiar de almacén rápidamente:
   consultar de nuevo al volver y no sobrescribir una consulta nueva con una respuesta vieja.
9. `[ ]` PostgreSQL: enviar tickets simultáneos P1/P2 y P2/P1; comprobar que ambos bloquean
   en el mismo orden y no dejan stock negativo. Forzar insuficiencia en segunda línea:
   no deben persistir orden, primera línea ni movimientos. Repetir con IDs de otro negocio,
   almacén inactivo, cantidades inválidas, líneas repetidas y USD/VES mezclados.
10. `[ ]` Verificar que totales y moneda de la confirmación coinciden con la respuesta del
    servidor y que el dashboard recibe la venta completada del canal presencial.

Idempotencia persistente, reservas y sesiones de caja permanecen pendientes. No se deben
marcar como verificadas por el bloqueo local de botones ni por las pruebas con dobles.

## Séptimo bloque: ejecución reproducible de diagnóstico e integración

Bases revisadas: backend `2b133cc`, frontend `adb8a23`, ambos limpios en `dev`.

- `[x]` Compilación Python de diagnóstico, configuración, suite de integración, revisión
  de despliegue, rutas y smoke. Compilar la suite no significa que sus casos hayan pasado.
- `[x]` `python3 -m unittest discover -s tests -v`: 34 pruebas locales aprobadas. Las siete
  nuevas verifican rechazo de configuración ausente/no QA, ausencia de secretos en errores,
  nombre separado de base de pruebas y publicación exclusiva de revisiones válidas.
- `[x]` `npx tsc --noEmit`: frontend sin cambios y salida idéntica a la anterior, con los
  mismos 75 errores preexistentes.
- `[x]` Railway confirmó la revisión `7d5b8e69090bcfc897c4f34a6ea20d0b16081951` después
  del push. El smoke con `--expected-revision` pasó sus ocho rutas; esto acredita el código
  desplegado y el rechazo anónimo, no el diagnóstico SQL ni los casos autenticados.
- `[ ]` Ejecutar `diagnostico_inventario` en Railway y guardar su informe sanitizado.
- `[ ]` Ejecutar los 15 casos de `store.test_inventario_integration` contra PostgreSQL QA.
- `[ ]` Usar cuentas QA para la prueba visual en Android y revisar logs del 502 anterior.

### Diagnóstico en el servicio de Railway

Desde una sesión de terminal del servicio con el código actualizado y su entorno Django,
ejecutar (no ejecutar localmente bajo las convenciones actuales):

```bash
python manage.py diagnostico_inventario --limit 20
```

El comando no llama a `migrate`, no crea archivos ni corrige stock. PostgreSQL impone
solo lectura y un límite de 15 segundos por consulta. Si hay migraciones de `store`
pendientes o conflictos, omite la consulta de inventario; `inventario: null` no significa
inventario correcto. `--skip-stock` permite revisar sólo migraciones/revisión;
`--check` sale con error si el informe requiere revisión.

Guardar `migraciones_store_pendientes`, `conflictos_migraciones`,
`cambios_modelos_sin_migracion` e `inventario`. Revisar todas las operaciones propuestas:
la diferencia de `MovimientoStock.origen` detectada antes puede no ser la única.
El diagnóstico no demuestra la causa del 502; se necesitan los logs de aquel despliegue.

Para comprobar el commit servido desde cualquier equipo sin credenciales:

```bash
python3 scripts/smoke_inventory_routes.py https://backend-ojeda-app-production.up.railway.app --expected-revision <SHA_COMPLETO>
```

La comprobación falla si el servidor no expone revisión o todavía sirve otra. Sin el
argumento conserva el smoke anónimo anterior. Railway documenta el SHA para despliegues
disparados desde GitHub en su [referencia de variables](https://docs.railway.com/variables/reference#git-variables).

### Suite PostgreSQL en un entorno de pruebas preparado

Requiere las dependencias del backend instaladas, su configuración de arranque válida y
`TUPLAZA_TEST_DATABASE_URL` configurada como secreto del entorno, apuntando a un servidor
PostgreSQL de QA con base `tuplaza_qa_inventario` (u otro sufijo). El usuario de conexión debe
poder crear/eliminar **la base de prueba**; no reutilizar el servidor ni las credenciales
operativas. No pegar la URL con contraseña en documentación ni en resultados de pruebas.

```bash
python manage.py test store.test_inventario_integration --settings=backend_ojeda.integration_settings --noinput
```

El runner crea `test_tuplaza_qa_inventario`, aplica las migraciones existentes, genera cuentas
con dominio `.invalid`, tiendas y productos de prueba, y elimina esa base al finalizar.
Si el nombre ya existe, `--noinput` permite recrearlo: reservar ese nombre exclusivamente
para esta suite. La base fuente `tuplaza_qa_inventario` no es el destino de los fixtures.
Fuera de `integration_settings`, esta clase se omite. Nunca activar estos settings en el
servicio desplegado ni usar `--keepdb` para presentar como reproducible una base modificada.

Los 15 casos cubren venta por almacén, rollback completo, líneas repetidas, aislamiento
REST/JWT, cliente/anónimo, miembro desactivado, almacén inactivo, servicios y monedas,
conteo principal, transferencia con tercer almacén, última unidad en dos cajas, deltas
simultáneos, tickets en orden inverso, transferencias opuestas y diagnóstico sin reparación.
La concurrencia usa conexiones por hilo y barrera de inicio; las conexiones tienen límites
de consulta/bloqueo. Esto prueba solicitudes concurrentes, no idempotencia ni Android.

Referencias de implementación: [base de pruebas de Django 5.1](https://docs.djangoproject.com/en/5.1/topics/testing/overview/#the-test-database)
y [autodetección de migraciones de Django](https://github.com/django/django/blob/5.1.4/django/core/management/commands/makemigrations.py).
No se ejecutó Django localmente: sigue aplicando `CONVENTIONS.md`.

## Historial de inventario filtrable y paginado (2026-09-09)

Implementado en **Mis productos → historial de stock del producto**. No requiere migraciones.

Contrato de `GET /api/store/productos-tienda/{id}/movimientos/`:

- Sin parámetros conserva el array de hasta 50 movimientos recientes por fecha.
- `paginado=1` devuelve `{"results": [...], "siguiente_antes_de": 123}`; enviar
  `antes_de=123` para continuar. Cursor `null` indica fin. Páginas ordenadas por ID
  descendente, máximo 50 filas; las entradas nuevas se consultan al actualizar el historial.
- Filtros opcionales: `almacen_id` positivo (incluye almacenes inactivos), `origen`
  (`venta_presencial`, `orden_online`, `ajuste_manual`, `creacion`, `transferencia`) y
  `dias` (`7`, `30`, `90`, intervalo móvil calculado en cada consulta). Omitir `dias`
  consulta todas las fechas. Los filtros se aplican antes de limitar la página.
- Un parámetro inválido devuelve `400` con `detail` en español. `antes_de` requiere
  `paginado=1`. Los movimientos sin almacén siguen incluidos al seleccionar “Todos”.
- La ruta conserva autenticación, rol tienda y verificación del producto propio. Filtrar
  por un almacén sin movimientos de ese producto devuelve una página vacía.

Verificación realizada:

- `[x]` Compilación de vistas, serializers, servicio de historial y pruebas con `py_compile`.
- `[x]` `python3 -m unittest discover -s tests -v`: 43 pruebas correctas; 9 del historial
  cubren 125 movimientos, inserción entre páginas, límites de 50/51, filtros combinados,
  inclusión del límite temporal, registros sin almacén y contrato anterior. Usan un doble
  de consulta; no acreditan SQL ni permisos reales.
- `[x]` `node --test scripts/stock-history.test.cjs`: 3 pruebas correctas de parámetros,
  autenticación/timeout y compatibilidad. Una respuesta antigua sin filtros se rechaza.
- `[x]` `npx tsc --noEmit`: mismos 75 errores preexistentes, salida idéntica antes/después.
- `[x]` Smoke previo al push en Railway: salud `200` y ocho rutas administrativas `401`,
  incluida la consulta de movimientos con filtros. Verifica disponibilidad y autenticación
  requerida; no acredita el resultado de una consulta autenticada.

Validación funcional pendiente, sin bloquear los siguientes desarrollos:

- `[ ]` Con más de 50 movimientos, recorrer todas las páginas y confirmar que los IDs no
  se repiten. Registrar otra entrada entre páginas y verla al actualizar.
- `[ ]` Combinar almacén, origen y período; confirmar saldos históricos mostrados y que
  no se mezclan ubicaciones. Consultar un almacén inactivo y movimientos sin almacén.
- `[ ]` Cambiar filtros rápidamente con red lenta; no mostrar respuestas del filtro anterior.
  Cortar la red al cargar anteriores: conservar lo ya leído y reintentar la misma página.
- `[ ]` Volver de renombrar un almacén y confirmar el nuevo nombre. Si falla la consulta de
  ubicaciones, conservar el contexto del filtro y ofrecer reintentar su carga.
- `[ ]` Probar parámetros inválidos, usuario cliente y producto de otro negocio con sesión;
  comprobar rechazo sin devolver movimientos ajenos.
- `[ ]` Probar una app anterior: recibe un array y conserva el historial original.

## Pruebas de aislamiento y permisos

- `[ ]` Un usuario no puede consultar el negocio de otra tienda modificando IDs.
- `[ ]` Un miembro de negocio A no puede listar productos, órdenes, caja o inventario de B.
- `[ ]` Un cliente no puede crear/editar sucursales, almacenes, precios o stock.
- `[ ]` Un administrador no puede modificar datos exclusivos del propietario.
- `[ ]` Un usuario eliminado o desactivado pierde acceso a la operación.
- `[ ]` Las rutas REST y GraphQL aplican las mismas reglas de pertenencia.
- `[ ]` Los errores de autorización no revelan si existe información de otro negocio.

## Pruebas de inventario y POS

- `[ ]` Una venta descuenta sólo del almacén seleccionado.
- `[ ]` Dos ventas simultáneas no producen stock negativo.
- `[ ]` Un doble toque, timeout o reintento no duplica la venta.
- `[ ]` Una orden pendiente reserva stock sólo durante el tiempo definido.
- `[ ]` Cancelar una orden libera la reserva correctamente.
- `[ ]` Completar una orden descuenta una sola vez.
- `[ ]` Devolver una venta crea un movimiento inverso auditable.
- `[ ]` Un servicio no descuenta inventario.
- `[ ]` Una transferencia conserva cantidades y trazabilidad en origen/destino.
- `[ ]` Una venta presencial descuenta del almacén seleccionado desde la app.
- `[ ]` Un ajuste manual modifica sólo el almacén seleccionado desde la app.
- `[ ]` El código de barras no puede apuntar a un producto de otro negocio.

## Pruebas financieras

- `[ ]` Una operación conserva importe original, moneda, tasa y monto normalizado.
- `[ ]` Confirmar un pago una sola vez es idempotente.
- `[ ]` Rechazar un pago no altera indebidamente el inventario.
- `[ ]` Un movimiento confirmado no se edita: se revierte o ajusta.
- `[ ]` El cierre de caja concilia efectivo esperado contra efectivo contado.
- `[ ]` El diferencial cambiario usa la tasa de emisión y la tasa de liquidación correctas.
- `[ ]` Los reportes coinciden con la suma de operaciones auditadas.

## Pruebas offline y recuperación

- `[ ]` El POS permite preparar una operación sin conexión cuando el catálogo está
  sincronizado.
- `[ ]` Cada operación offline recibe un identificador único.
- `[ ]` La cola reintenta después de recuperar internet.
- `[ ]` Un reintento del mismo identificador no duplica dinero ni stock.
- `[ ]` Un conflicto se muestra y resuelve según una regla definida.
- `[ ]` La app comunica claramente operaciones pendientes de sincronización.
- `[ ]` Reiniciar la app no borra la cola local.

## Pruebas de seguridad y archivos

- `[ ]` Rate limits funcionan por usuario/IP y no dependen de memoria local en producción.
- `[ ]` Se rechazan imágenes/PDF corruptos, demasiado grandes o con tipo real incorrecto.
- `[ ]` Los comprobantes no quedan accesibles sin autorización.
- `[ ]` Los logs no contienen contraseñas, JWT, códigos OTP ni comprobantes completos.
- `[ ]` URLs de archivos expiran cuando se habiliten URLs firmadas.
- `[ ]` Cambios de precio, stock, pagos, caja y permisos generan auditoría.
- `[ ]` Backup y restauración se prueban en un entorno separado.

## Pruebas de regresión por pantalla

- `[ ]` Inicio y navegación inferior.
- `[ ]` Productos, servicios, comidas y segunda mano.
- `[ ]` Perfil público y perfil propio de tienda.
- `[ ]` Registro/edición de tienda y categorías.
- `[ ]` Mis productos y movimientos de stock.
- `[ ]` Caja/POS.
- `[ ]` Mis pedidos y seguimiento de órdenes.
- `[ ]` Solicitud/seguimiento de taxi, delivery y encomienda.
- `[ ]` Chat, adjuntos, ubicación y notificaciones.
- `[ ]` Wishlist, carrito, checkout y pagos.
- `[ ]` Login, Google, recuperación de contraseña y logout.

## Evidencia y criterio de aprobación

Para cada bloque terminado guardar:

- `[ ]` Fecha, versión de APK y commit probado.
- `[ ]` Entorno y URL/API utilizada.
- `[ ]` Usuario y rol de prueba, sin incluir contraseñas.
- `[ ]` Resultado de migraciones y comandos ejecutados.
- `[ ]` Capturas o video de la app cuando el comportamiento sea visual.
- `[ ]` Request/response sanitizados para errores de API.
- `[ ]` Incidencias encontradas, severidad y decisión.

Un bloque puede marcarse como listo cuando no tenga fallos críticos, sus permisos estén
probados, la migración sea reproducible, la app tenga fallback si el backend no está
actualizado y el smoke test no presente regresiones.
