# Roadmap backend — hacia paridad funcional con Fina Partner

Mapa de fases con checkboxes para ir cerrando la brecha con Fina Partner (ver
`Análisis y Réplica Fina Partner.pdf`). Este archivo es el resumen navegable;
el detalle de implementación, contratos de API y evidencia de cada paso vive en
`fina-partner-gap-checklist.md` (análisis de brecha completo) y
`fina-partner-test-plan.md` (plan de pruebas). No dupliques ahí el detalle: si
una tarea nueva se implementa, actualiza esos dos documentos y sólo mueve el
checkbox correspondiente aquí.

Contraparte en la app: `TuPlazaFront/ROADMAP.md`.

## Convención

- `[x]` Hecho y validado end-to-end (API + permisos + pruebas reales).
- `[~]` Implementado pero con validación pendiente (Android, PostgreSQL real,
  concurrencia) — ver el gap-checklist para el detalle exacto de qué falta.
- `[ ]` No empezado.
- `[-]` Fuera de alcance por ahora (depende de terceros/regulación/decisión de
  negocio pendiente).

**Estado revisado:** 2026-09-14, sobre `dev` + cuentas por cobrar, por pagar y gastos (ver Fase 2).

## Fase 0 — Fundaciones (multi-tenant)

- `[~]` `Negocio` / `NegocioMiembro` como tenant, creación automática por tienda.
- `[~]` `Sucursal` / `Almacen` con estructura principal automática.
- `[ ]` Revisión sistemática de aislamiento por tenant en cada vista/resolver
  (hoy es filtrado manual por `tienda`/`negocio`, sin capa común obligatoria).
- `[ ]` Evaluar Row-Level Security de PostgreSQL (sólo cuando el modelo de
  pertenencia esté cerrado; no bloquea el resto de fases).

## Fase 1 — Núcleo operativo (POS, inventario, caja)

- `[~]` Inventario por almacén + transferencias atómicas.
- `[~]` Venta presencial idempotente (`OperacionVentaPresencial`, UUID,
  cancelación, replay seguro).
- `[~]` Sesión de caja: apertura, movimientos, cierre/arqueo por moneda
  (migración `0041`).
- `[ ]` Reservas de stock para órdenes online (se revirtió por un 502 en
  Railway — commits `8082c31`/`346659a`; retomar después de diagnosticar esa
  caída, no antes).
- `[ ]` Costo promedio ponderado calculado de forma transaccional.
- `[ ]` Importador CSV/Excel de catálogo, precios y existencias.
- `[ ]` Variantes con SKU propio (talla/color/modelo) en el modelo de producto.

## Fase 2 — Finanzas y resiliencia

- `[~]` Cuentas por pagar a proveedores: `CuentaPorPagar`, `AbonoCuentaPorPagar`,
  `OperacionCuentaPorPagar` (migración `0043`), servicio `store/services/pagos.py`
  (mismo patrón que cuentas por cobrar, con el signo del diferencial cambiario
  invertido: tasa al alza = pérdida, no ganancia), endpoints en
  `/api/store/cuentas-pagar/` y pantalla en TuPlazaFront (`AccountsPayable.tsx`).
  Falta: entidad `Proveedor` propia con condiciones de pago (sin datos fiscales,
  ver sección de alcance de producto), órdenes de compra, alertas de
  vencimiento y validación Android/PostgreSQL.
- `[~]` Clientes con crédito comercial y cuentas por cobrar: `CuentaPorCobrar`,
  `AbonoCuentaPorCobrar`, `OperacionCuentaPorCobrar` (migración `0042`),
  servicio `store/services/cuentas.py`, endpoints idempotentes en
  `/api/store/cuentas-cobrar/` y pantalla en TuPlazaFront
  (`AccountsReceivable.tsx`). Falta: alertas de vencimiento automáticas y
  validación Android/PostgreSQL.
- `[~]` Gastos fijos/variables por sucursal: `Gasto`, `OperacionGasto` (migración
  `0044`), servicio `store/services/gastos.py`, endpoints en `/api/store/gastos/`
  y pantalla en TuPlazaFront (`Expenses.tsx`). Falta: comprobante adjunto (foto/PDF
  — se dejó fuera de este primer corte para no mezclar subida de archivos con el
  patrón de operación idempotente en JSON), reporte de utilidad neta y validación
  Android/PostgreSQL.
- `[~]` Offline-first real en Modo caja: `offlineSalesQueue.ts` en TuPlazaFront
  (2026-09-14) — cola de múltiples ventas sin conexión, cada una con su propia
  clave idempotente contra el endpoint ya existente de venta presencial. Decisión
  de producto: se permite cobrar con la última existencia conocida cuando falla
  la consulta en vivo (con aviso al cajero); un rechazo del servidor por falta
  de stock real al sincronizar queda marcado "Requiere atención". Sin catálogo
  de productos cacheado todavía — sólo resuelve el cobro de un ticket ya armado.
- `[~]` Diferencial cambiario realizado al liquidar una cuenta
  (ΔC = monto_usd_abonado·(T2−T1)): implementado en `registrar_abono()`,
  cubierto por 12 pruebas con dobles de ORM. Sigue faltando un libro mayor
  (ledger) que agregue estos asientos en un solo reporte por negocio/sucursal
  — hoy cada abono guarda su propio diferencial, sin vista consolidada.
- `[ ]` Idempotencia por UUID extendida a toda operación con dinero o stock
  (ya cubre venta presencial, caja y ahora cuentas por cobrar).
- `[ ]` Ejecutar la suite de integración PostgreSQL ya escrita
  (`store/test_inventario_integration.py`) y las pruebas de concurrencia
  descritas en `fina-partner-test-plan.md`; hoy están preparadas, no corridas.
- `[ ]` Backups verificados y plan de recuperación ante desastre.

## Fase 3 — Verticales

- `[ ]` Recetas/BOM (gastronomía): descuento atómico de insumos al vender un
  plato, ajuste del CPP.
- `[ ]` Lotes + fecha de vencimiento + despacho FEFO (farmacia/perecederos).
- `[ ]` Variantes talla/color (moda) — depende del catálogo de Fase 1.
- `[ ]` Números de serie/IMEI + garantía (tecnología).
- `[ ]` Matriz de compatibilidad + unidades fraccionarias (repuestos/ferretería).

## Fase 4 — Ecosistema

- `[ ]` Roles granulares (cajero, despachador, solo lectura) — hoy sólo existen
  `owner`/`admin` en `NegocioMiembro`.
- `[ ]` Auditoría inmutable de cambios sensibles (precio, stock, caja, usuarios,
  permisos).
- `[ ]` CRM: ficha de cliente por negocio, historial, RFM, campañas.
- `[-]` Cashea (BNPL) — depende de contrato/API/credenciales del proveedor.
- `[-]` Pago Móvil C2P/P2C automatizado — depende de acuerdos bancarios.
- `[-]` Facturación fiscal SENIAT / bridge de impresoras fiscales — **fuera de
  alcance de producto** (decisión 2026-09-14): TuPlaza es para emprendimientos
  no fiscalizados, no sólo pospuesto por asesoría legal pendiente.
- `[ ]` Asistente IA tipo Nina (Text-to-SQL de solo lectura, réplica separada,
  guardrails de tenant obligatorio).

## Próximo paso recomendado

1. Diagnosticar y cerrar el 502 que bloqueó las reservas de inventario (Fase 1)
   antes de sumar módulos nuevos sobre una base sin validar.
2. Correr la suite PostgreSQL de integración ya escrita — es lo único que puede
   mover los `[~]` actuales a `[x]`, incluyendo el bloque de cuentas por
   cobrar recién añadido.
3. Comprobante adjunto para cada gasto (foto/PDF) y reporte de utilidad neta que
   combine gastos con ventas. Proveedores con condiciones de pago (sin datos
   fiscales, ver sección de alcance) — hoy `CuentaPorPagar` sólo guarda nombre y
   teléfono libres, sin entidad `Proveedor` propia.
