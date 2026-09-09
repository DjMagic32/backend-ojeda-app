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
