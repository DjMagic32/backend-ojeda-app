# Checklist de brecha: capacidades tipo Fina Partner para TuPlaza

Documento de trabajo para evaluar qué necesitamos para que los negocios que operan en
TuPlaza tengan capacidades parecidas a un sistema administrativo como Fina Partner.

## Cómo usar este documento

- `[x]` Cubierto actualmente en TuPlaza.
- `[~]` Parcial: existe una base, pero falta una parte importante para considerarlo listo.
- `[ ]` Pendiente.
- `[-]` Fuera del alcance inmediato o depende de un tercero/regulación.

Una casilla sólo debe pasar a `[x]` cuando exista el modelo y la migración, la API protegida,
los permisos, las validaciones transaccionales, las pruebas y la pantalla que la consuma.

Cuando una capacidad tenga varias capas, se registrará por separado: **API**, **app** y
**operación/despliegue**. Que exista el endpoint no significa que la capacidad esté terminada
para el usuario.

**Referencia funcional:** `Análisis y Réplica Fina Partner.pdf` (documento entregado para
este análisis). El PDF se usa como referencia de capacidades, no como especificación literal
ni como afirmación independiente de sus cifras comerciales.

**Estado revisado:** 2026-09-08
**Código revisado principalmente:** `store/models.py`, `store/views.py`,
`store/graphql/schema.py`, `store/services/inventario.py` y
`store/analytics/predicciones.py`.

### Avance del primer paso

- **API:** `[x]` `Negocio`, `NegocioMiembro`, migración de datos existentes, creación
  automática para nuevas tiendas y `GET /api/store/mi-negocio/`.
- **App:** `[x]` consume el endpoint de forma tolerante a errores y muestra el contexto del
  negocio activo en el perfil de la tienda, sin bloquear el catálogo si el backend aún no
  tiene aplicada la migración.
- **Operación:** `[x]` las migraciones del módulo fueron ejecutadas en Railway; la respuesta
  confirmó que no había migraciones pendientes y no se borraron datos.

### Avance del segundo paso

- **API:** `[x]` `Sucursal` y `Almacen`, códigos únicos, estructura principal automática,
  endpoints protegidos de alta/edición/desactivación y datos anidados en
  `GET /api/store/mi-negocio/`.
- **App:** `[x]` el perfil de la tienda muestra el resumen y existe una pantalla para crear
  y desactivar sucursales y almacenes.
- **Operación:** `[x]` la migración `0037_sucursal_almacen` quedó aplicada en Railway junto
  con el resto de migraciones del proyecto; falta validar los datos reales con usuarios de
  prueba.
- **Alcance pendiente:** falta asignarla al inventario y transferir existencias; la pantalla
  actual no permite todavía renombrar registros existentes.

### Avance del tercer paso

- **API:** `[~]` se agregó `InventarioAlmacen`, la migración `0038_inventario_almacen`,
  consulta protegida por negocio en `GET /api/store/inventario-almacenes/`, asociación del
  stock existente al almacén principal, registro de movimientos con almacén y transferencia
  atómica entre almacenes mediante `POST /api/store/transferencias-inventario/`. Las ventas
  y ajustes antiguos siguen usando automáticamente el almacén principal cuando existe.
- **App:** `[~]` la pantalla de sucursales y almacenes muestra cuántos productos están
  asociados a cada almacén, el historial de stock muestra la sucursal/almacén del movimiento
  y hay una pantalla para transferir existencias. Todavía falta seleccionar el almacén
  explícitamente desde ventas/ajustes.
- **Operación:** `[x]` `0038_inventario_almacen` y `0039_transferencia_inventario` fueron
  ejecutadas en Railway. Django dejó una advertencia sobre cambios de modelos sin migración
  equivalente; no se debe marcar el bloque completo hasta revisar ese aviso y probar datos
  reales.

### Avance del cuarto paso

- **API:** `[x]` las ventas presenciales aceptan un `almacen_id` opcional, verifican que el
  almacén pertenezca al negocio de la tienda y registran la salida en ese almacén. Los
  ajustes ya usan el mismo mecanismo; sin `almacen_id` se conserva el almacén principal.
- **App:** `[x]` “Mis productos” y “Modo caja” cargan los almacenes activos y permiten elegir
  dónde se aplica el ajuste o la venta.
- **Operación:** `[x]` no requiere una migración adicional; el cambio es compatible con el
  endpoint anterior y el fallback del almacén principal.
- **Pruebas:** `[ ]` falta comprobar con dos almacenes, stock insuficiente, servicios y
  permisos de un almacén de otra tienda.

## Conclusión ejecutiva

Sí, podemos hacerlo, pero Fina Partner y TuPlaza parten de productos distintos:

- **TuPlaza** ya es un marketplace con tiendas, productos/servicios, pedidos, pagos,
  reputación, chat y delivery.
- **Fina Partner** es principalmente el sistema operativo interno del negocio: POS,
  inventario avanzado, caja, compras, gastos, cuentas pendientes, reportes y operación
  offline.

La estrategia recomendada es crear un **módulo opcional de gestión del negocio** para las
tiendas. No debemos mezclar los artículos de segunda mano de usuarios comunes con el
ERP de una tienda ni exigirles configurar una tienda para vender en el marketplace.

### Lo más importante que falta

1. Aislamiento formal de negocio y sucursales/almacenes.
2. Inventario transaccional avanzado y un POS que también funcione con mala conexión.
3. Caja, gastos, proveedores, cuentas por cobrar/pagar y libro financiero bimonetario.
4. Usuarios internos de la tienda, permisos granulares y auditoría.
5. Importación desde Excel/CSV para que un negocio pueda migrar sin cargar todo a mano.
6. Funcionalidades verticales: variantes, lotes, recetas, seriales y unidades.
7. Facturación fiscal e integraciones financieras, que deben ir después del núcleo.

## 1. Alcance del negocio y aislamiento de datos

### Estado actual

- `[~]` `Tienda` funciona como dueño lógico del catálogo, las órdenes, los pagos y el
  dashboard.
- `[~]` Un usuario puede tener rol de tienda, cliente o conductor, pero no existe todavía
  una cuenta empresarial con varios usuarios internos y varias sucursales.
- `[~]` Introducir una entidad `Business/Tenant` explícita. La API ya la materializa como
  `Negocio` y cada tienda existente recibe uno mediante la migración
  `0036_negocio_negociomiembro`; la app ya muestra el contexto del negocio cuando está
  disponible. Inicialmente se asocia a una `Tienda`, pero conviene separar el concepto para
  no bloquear una futura empresa con varias sucursales.
- `[ ]` Añadir `tenant_id` a los modelos administrativos que correspondan y definir reglas
  de aislamiento a nivel de servicio y base de datos.
- `[ ]` Evaluar Row-Level Security (RLS) de PostgreSQL cuando el módulo sea multiempresa;
  no conviene activarlo sin antes cerrar el modelo de pertenencia y las migraciones.
- `[~]` Crear `Sucursal` y `Almacen`: ya existe la estructura principal en API y app, el
  inventario se asocia al almacén principal y la app permite transferir entre almacenes;
  faltan recepción formal, controles avanzados y operaciones por ubicación más completas.
- `[x]` Definir qué permanece global de TuPlaza (marketplace, usuarios, delivery) y qué
  pertenece exclusivamente al negocio (ventas internas, compras, gastos y caja).

### Decisión de arquitectura

La orden del marketplace (`StoreOrder`) no debería cargar por sí sola todo el futuro ERP.
Recomendación: mantenerla para compras dentro de TuPlaza y crear una entidad de venta/caja
que pueda recibir ventas online, presenciales y futuras ventas importadas, relacionadas con
el negocio y la sucursal correspondiente.

## 2. Catálogo de productos y servicios

- `[x]` Publicación de productos y servicios con nombre, descripción, precio, moneda,
  imágenes, stock opcional, categoría y código de barras.
- `[x]` Categorías diferenciadas para productos/servicios y categorías marcadas como
  comida.
- `[x]` Productos destacados, reseñas/reputación de tienda y perfil público.
- `[~]` Costos unitarios y margen: existe `costo_unitario` y dashboard, pero faltan compras,
  gastos y un cálculo de utilidad neta confiable.
- `[ ]` Importador masivo de productos, precios, existencias y clientes desde CSV/Excel,
  con vista previa, errores por fila y reintento seguro.
- `[ ]` Variantes con SKU propio por talla, color, modelo u otra combinación de atributos.
- `[ ]` Listas de precios por cliente, canal, sucursal o temporada.
- `[ ]` Unidades de medida y conversiones (unidad, caja, kilo, litro, fracción).
- `[ ]` Matriz de compatibilidad para repuestos, ferretería u otros catálogos técnicos.

## 3. Inventario

- `[x]` Ajustes manuales y movimientos de stock asociados a ventas presenciales y órdenes.
- `[x]` Consulta de movimientos y validación para evitar stock negativo en las operaciones
  actuales.
- `[~]` Reservas de inventario para órdenes online: existe el flujo de pedido, pero debemos
  definir una reserva con vencimiento para evitar vender dos veces la misma existencia.
- `[~]` Existencias por sucursal y almacén: existe el detalle transaccional, la migración del
  stock legado, asociación automática al almacén principal y consulta protegida; falta la
  operación completa por almacén desde la app.
- `[~]` Transferencias entre almacenes: existe operación atómica con salida/entrada trazables
  y pantalla de prueba; faltan recepción formal, mermas, devoluciones y conteos físicos.
- `[ ]` Costo promedio ponderado calculado de forma transaccional.
- `[ ]` Lotes, fechas de vencimiento, alertas y despacho FEFO para alimentos, farmacias y
  perecederos.
- `[ ]` Recetas/BOM para comida, con descuento atómico de ingredientes al vender un plato.
- `[ ]` Números de serie, IMEI, garantía y trazabilidad por unidad para tecnología.
- `[ ]` Alertas configurables de reposición, rotación baja y productos agotados.
- `[ ]` Historial completo de quién hizo cada ajuste y por qué.

## 4. Ventas y punto de venta (POS)

- `[x]` Venta presencial básica desde `VentaPresencialCreateView`, con múltiples líneas,
  descuento de inventario y soporte de código de barras en la app.
- `[x]` Pedido online con items, estado, pago reportado/confirmado y comprobante.
- `[~]` Dashboard de tienda y separación de canal online/presencial; falta convertirlo en
  cierre operativo de caja y reportes contables.
- `[ ]` Sesión de caja: apertura, fondo inicial, movimientos, retiros, cierre y arqueo.
- `[ ]` Ticket/factura con numeración, devolución, anulación y nota de crédito.
- `[ ]` Cotizaciones que puedan convertirse en venta sin volver a registrar los productos.
- `[ ]` Cargos configurables: delivery, empaque, propina, comisión, descuento e impuestos.
- `[ ]` Comandas, mesas y estados de cocina para restaurantes.
- `[ ]` Venta omnicanal unificada: marketplace, POS, enlaces externos y venta manual.
- `[ ]` Idempotencia por operación para que un doble toque o reintento de red no cree dos
  ventas.

## 5. Tesorería y operación bimonetaria

- `[x]` Precios en USD/VES, tasa vigente y snapshot de la tasa al crear una orden.
- `[x]` Métodos actuales de pago, reporte de pago y captura de comprobante.
- `[~]` Wallet y pagos existen, pero no sustituyen un libro de caja ni una conciliación
  bancaria.
- `[ ]` Cuentas de efectivo, bancos, Pago Móvil y otras cuentas por negocio/sucursal.
- `[ ]` Registro de cada entrada y salida con moneda original, tasa, monto normalizado y
  referencia.
- `[ ]` Arqueo de caja y conciliación contra saldo esperado.
- `[ ]` Conciliación de transferencias/Pago Móvil mediante importación o webhook cuando el
  banco lo permita.
- `[ ]` Libro mayor/ledger con asientos inmutables y trazabilidad de origen.
- `[ ]` Diferencial cambiario realizado al momento de cobrar una cuenta emitida con otra
  tasa.
- `[ ]` Reportes de flujo de caja, ingresos, egresos, utilidad bruta y utilidad neta.

La regla de diseño debe ser: nunca sobrescribir un movimiento financiero confirmado;
cualquier corrección debe generar reverso o ajuste auditable.

## 6. Compras, proveedores y cuentas pendientes

- `[ ]` Proveedores con datos fiscales, contactos y condiciones de pago.
- `[ ]` Orden de compra, recepción parcial/total y entrada automática al inventario.
- `[ ]` Cuentas por pagar con vencimiento, abonos, saldo y alertas.
- `[ ]` Crédito comercial a clientes y cuentas por cobrar.
- `[ ]` Historial de pagos parciales y estados vencido/por vencer.
- `[ ]` Reporte de antigüedad de saldos y recordatorios configurables.

## 7. Gastos y rentabilidad

- `[ ]` Gastos fijos y variables categorizados por negocio, sucursal y período.
- `[ ]` Adjuntar comprobantes de gasto (imagen/PDF), aplicando las mismas validaciones de
  archivos ya usadas en uploads.
- `[ ]` Reglas para separar costo de producto, gasto operativo, delivery, comisión y otros
  cargos.
- `[ ]` Estado de resultados básico y margen por producto/categoría/canal.
- `[ ]` Proyección de flujo de caja basada en ventas y compromisos pendientes.

## 8. Clientes, CRM y fidelización

- `[x]` Usuarios compradores, historial de pedidos, chat, reseñas y reputación.
- `[~]` La tienda puede consultar órdenes y métricas, pero aún no tiene un CRM operacional
  con segmentos y acciones comerciales.
- `[ ]` Ficha de cliente para el negocio con historial de compras, frecuencia, último pedido,
  saldo y consentimiento de comunicación.
- `[ ]` Segmentación RFM (recencia, frecuencia y valor monetario).
- `[ ]` Clientes frecuentes, beneficios, cupones o lista de precios.
- `[ ]` Campañas de reactivación por canales autorizados. SMS masivo requiere proveedor,
  consentimiento, límites y control de abuso.

## 9. Usuarios internos, permisos y auditoría

- `[~]` Existen roles globales de TuPlaza y permisos de propietario para varias operaciones.
- `[ ]` Miembros internos de una tienda con invitación, activación y revocación.
- `[ ]` Roles granulares: propietario, administrador, caja, almacén, ventas, despacho y
  solo lectura.
- `[ ]` Permisos por acción, sucursal y almacén.
- `[ ]` Auditoría inmutable de cambios sensibles: precio, stock, pagos, órdenes, caja,
  usuarios y datos fiscales.
- `[ ]` Registro de inicio de sesión, dispositivo y eventos administrativos relevantes.
- `[ ]` Política de retención y exportación de auditoría para el negocio.

## 10. Resiliencia, offline-first e infraestructura

- `[x]` API protegida, JWT, rate limits, validación de uploads y WebSockets para eventos
  de la aplicación actual.
- `[~]` Redis/Channels está contemplado para tiempo real, pero la operación POS offline y
  la reconciliación no están implementadas.
- `[ ]` POS web/PWA offline-first con catálogo local y cola de ventas.
- `[ ]` UUID/idempotency key por venta, pago, movimiento e importación.
- `[ ]` Sincronización por lotes al recuperar conexión, con resolución de conflictos.
- `[ ]` Bloqueos transaccionales y pruebas de concurrencia para inventario y caja.
- `[ ]` Backups verificados, restauración probada, retención y plan de recuperación ante
  desastre.
- `[ ]` Monitoreo de errores, latencia, colas, WebSockets, pagos y tareas programadas.
- `[ ]` Alertas operativas y trazas con un identificador de correlación por operación.
- `[ ]` Almacenamiento de archivos con URLs firmadas/expiración y política de eliminación.

## 11. Fiscalidad e integraciones externas

- `[ ]` Definir con asesoría local el alcance fiscal de TuPlaza y las obligaciones de cada
  tipo de negocio.
- `[ ]` Numeración fiscal, impuestos, libros de compra/venta y retenciones según aplique.
- `[ ]` Integración con un proveedor de facturación electrónica autorizado, si el negocio
  lo necesita.
- `[ ]` Bridge local para impresoras fiscales, sólo después de validar modelos de hardware
  y requisitos regulatorios.
- `[-]` Integración BNPL/Cashea: depende de contrato, documentación, credenciales,
  compliance y aprobación del proveedor.
- `[-]` Integración directa con bancos/Pago Móvil: depende de disponibilidad de APIs,
  acuerdos comerciales y requisitos de seguridad.

No conviene prometer homologación fiscal ni pagos automáticos sólo por implementar los
endpoints: ambos requieren validación legal, contractual y operativa en Venezuela.

## 12. Analítica e inteligencia artificial

- `[~]` Hay dashboard de tienda y un módulo de predicciones en backend; falta convertirlo
  en indicadores consistentes basados en costo, gastos, inventario y caja.
- `[ ]` Métricas operativas: ventas por período, margen, rotación, quiebres, ticket promedio,
  clientes nuevos/recurrentes y canal.
- `[ ]` Exportación de reportes y filtros por sucursal, categoría y moneda.
- `[ ]` Recomendaciones de reposición y detección de baja rotación.
- `[ ]` Asistente conversacional tipo Nina, restringido a datos del negocio y solo lectura.
- `[ ]` Capa analítica separada del OLTP para no ejecutar consultas pesadas sobre la base
  transaccional.
- `[ ]` Guardrails para IA: AST/allowlist de `SELECT`, tenant obligatorio, límites de
  tiempo/filas, réplica de solo lectura, auditoría y ausencia de datos sensibles en el
  prompt.
- `[-]` Scoring crediticio o préstamos: no es requisito del MVP y tiene implicaciones
  financieras, de privacidad y regulatorias.

## 13. Modelo de datos sugerido

Estas entidades representan una dirección, no una orden para crear todas las tablas de una
vez:

```text
Business/Tenant
  ├─ Sucursal
  │   └─ Almacen
  ├─ BusinessMember / Role / Permission
  ├─ Product / ProductVariant / Category
  │   ├─ InventoryBalance
  │   ├─ InventoryLot
  │   └─ Recipe/BOM
  ├─ Sale / SaleItem / Quote
  ├─ CashSession / CashMovement
  ├─ FinancialAccount / LedgerEntry / ExchangeRateSnapshot
  ├─ Supplier / Purchase / Payable
  ├─ CustomerProfile / Receivable
  ├─ Expense
  ├─ ImportJob / IdempotencyKey
  └─ AuditEvent
```

Reglas importantes:

- `StoreOrder` puede seguir representando una orden del marketplace; la venta consolidada
  debe permitir otras fuentes sin duplicar lógica.
- Todo registro administrativo debe poder responder: **a qué negocio, sucursal, almacén,
  usuario y operación pertenece**.
- Los importes deben guardar moneda original, tasa aplicada y monto normalizado cuando
  corresponda.
- Los cambios de estado de ventas, pagos, inventario y caja deben tener transiciones
  explícitas; no permitir que un recurso completado vuelva a un estado anterior.

## Roadmap recomendado

### Fase 0 — Fundaciones y decisiones

- `[x]` Confirmar que el objetivo es un módulo SaaS opcional para tiendas, no convertir a
  todos los usuarios del marketplace en empresas.
- `[~]` Definir `Business/Tenant`, membresías, sucursales y almacenes. Ya existen en API y
  app `Negocio`, `NegocioMiembro`, existencias por almacén y transferencias básicas; faltan
  controles operativos avanzados.
- `[x]` Definir la separación entre `StoreOrder`, `Sale`, delivery y artículos C2C.
- `[ ]` Especificar invariantes: no stock negativo, no doble cobro, no retroceso de estados,
  auditoría y permisos.

### Fase 1 — Núcleo operativo MVP

- `[ ]` Catálogo con variantes e importación CSV/Excel; las existencias por almacén ya tienen
  una base inicial, pero falta completar su operación.
- `[ ]` Venta/POS online y presencial unificada.
- `[ ]` Caja con apertura, cierre, arqueo y comprobante básico.
- `[ ]` Reservas de stock, devoluciones y movimientos auditables.
- `[ ]` Dashboard de ventas, stock y margen bruto.

### Fase 2 — Finanzas y resiliencia

- `[ ]` Gastos, proveedores, compras, cuentas por cobrar/pagar.
- `[ ]` Ledger bimonetario y diferencial cambiario.
- `[ ]` Conciliación de caja y bancos.
- `[ ]` Offline-first, cola idempotente y sincronización.
- `[ ]` Backups, monitoreo y pruebas de concurrencia.

### Fase 3 — Verticales de alto valor

- `[ ]` Comida: recetas/BOM, insumos, mermas y comandas.
- `[ ]` Moda: tallas, colores y variantes.
- `[ ]` Farmacia/alimentos: lotes, vencimientos y FEFO.
- `[ ]` Tecnología: seriales, IMEI y garantías.
- `[ ]` Repuestos/ferretería: unidades y compatibilidad.

### Fase 4 — Ecosistema

- `[ ]` CRM, segmentos, fidelización y campañas con consentimiento.
- `[ ]` Facturación fiscal/electrónica según el caso real de cada negocio.
- `[ ]` Integraciones bancarias o BNPL con acuerdos firmados.
- `[ ]` IA analítica de solo lectura después de tener datos financieros confiables.

## Criterio de terminado por módulo

Antes de declarar una capacidad lista para negocios reales, comprobar:

- `[ ]` Migración reversible o plan de migración documentado.
- `[ ]` Endpoints REST/GraphQL documentados y contratos de error claros.
- `[ ]` Autorización por negocio, sucursal, rol y propietario del recurso.
- `[ ]` Transacción atómica e idempotencia donde haya dinero, stock o estados.
- `[ ]` Auditoría de cambios sensibles.
- `[ ]` Pruebas de éxito, permisos, concurrencia, reintentos y datos incompletos.
- `[ ]` Estado visible en la app y sincronización WebSocket cuando corresponda.
- `[ ]` Métricas y logs sin exponer datos personales o credenciales.
- `[ ]` Manual corto para el negocio y procedimiento de recuperación.

## Orden de implementación sugerido para TuPlaza

El primer entregable no debería ser IA ni Cashea. La secuencia con mejor relación valor/riesgo
es:

1. `Business/Tenant` + miembros/permisos + sucursal/almacén.
2. Reservas y movimientos de inventario por almacén.
3. Venta/POS idempotente y sesión de caja.
4. Gastos, compras, proveedores y reportes de margen.
5. Ledger bimonetario y conciliación.
6. Offline-first y verticales según los primeros negocios reales.
7. Integraciones externas e IA con los datos ya confiables.

Así TuPlaza puede ofrecer a una tienda control real de su operación sin perder el marketplace,
el delivery ni el flujo simplificado para usuarios que sólo venden artículos ocasionalmente.
