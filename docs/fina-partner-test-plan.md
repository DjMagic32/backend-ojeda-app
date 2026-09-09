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
- **Operación:** `[ ]` ejecutar y probar la migración `0037_sucursal_almacen` en una base
  de datos de prueba/despliegue.
- **Pendiente funcional:** `[~]` la asociación inicial y la transferencia básica ya están
  implementadas; queda probarlas y completar recepción/controles avanzados.

### Estado de implementación del tercer bloque: inventario y transferencias

- **API:** `[~]` modelo `InventarioAlmacen`, migraciones `0038_inventario_almacen` y
  `0039_transferencia_inventario`, consulta protegida y transferencia atómica entre
  almacenes con movimientos de salida/entrada trazables.
- **App:** `[~]` resumen de productos asociados por almacén, historial con ubicación del
  movimiento y pantalla para transferir existencias; queda completar selección de almacén
  en ventas/ajustes y recepción avanzada.
- **Operación:** `[ ]` ejecutar `0038_inventario_almacen` y `0039_transferencia_inventario`
  en Railway y verificar las migraciones.
- **Pruebas:** `[ ]` ejecutar los casos de inventario con dos almacenes, transferencia
  insuficiente, concurrencia, servicios sin stock y compatibilidad con clientes antiguos.

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
