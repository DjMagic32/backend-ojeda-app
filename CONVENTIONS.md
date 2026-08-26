# Convenciones — backend-ojeda-app (Django 5.1 + DRF + graphene)

## Reglas de oro
- NO hay entorno local (ni Docker ni venv): NO ejecutar manage.py, ni
  makemigrations, ni runserver, ni tests de Django. Verificación =
  `python3 -m py_compile <archivos tocados>`.
- El deploy es Railway: hace auto-deploy y `migrate` al pushear a `dev`.
  Por eso las migraciones se escriben A MANO, copiando el estilo de
  `store/migrations/0023_*.py` y `0024_*.py` (dependencies correctas,
  swappable_dependency si hay FK a usuario, BigAutoField).
- ⚠️ Una migración rota BLOQUEA el deploy de Railway. Si una tarea exige
  una migración y no estás 100% seguro de escribirla correcta, NO la hagas:
  marca la tarea como fallida con el motivo y sigue con la siguiente.
- Campos nuevos en modelos existentes: SIEMPRE `null=True`/`blank=True` o
  `default=` (las apps viejas instaladas no deben romperse).
- Mensajes de error al cliente SIEMPRE en español, vía
  `ValidationError`/`Response({'detail': ...})`.
- Commits pequeños por tarea, mensaje en español, `git push origin dev`.

## Arquitectura
- UNA sola app: `store/`. Modelos en `store/models.py`, DRF en
  `serializers.py`/`views.py`/`urls.py`, GraphQL en `store/graphql/`
  (`types.py`, `schema.py`), signals en `signals.py`, servicios en
  `store/services/`.
- Auth: JWT (Bearer). Usuario custom `Usuario` con `rol`
  ('TIENDA','CLIENTE','CONDUCTOR'). Permiso `EsTienda` ya existe en views.
- Tienda del request: helper `_get_tienda_for_request()` en views.py.
- Stock: TODA escritura pasa por
  `store/services/inventario.py::registrar_movimiento` (select_for_update,
  crea MovimientoStock). Nunca modificar `ProductoTienda.stock` directo.
- Tasa de cambio: `TasaCambio.vigente()` y `tasa.valor_bs if tasa else None`.
  Nunca otro patrón.
- Órdenes: `StoreOrder` (canal 'online'/'presencial'; presencial nace
  estado='completed' con usuario=dueño). El dashboard (views.py, función
  de analytics ~línea 890) agrega sobre StoreOrders completed.
- Notificaciones push: signal `difundir_notificacion` / `notificar_orden`
  en signals.py + ExpoPushToken. Reusar ese mecanismo.
- GraphQL: tipos en types.py con `Meta.fields` explícitos; datos sensibles
  (ej. costo_unitario) con resolver que devuelve None si el user no es dueño.
- Moneda por producto ('USD'/'VES'); nunca mezclar monedas en una orden.

## Contexto de producto
- Marketplace venezolano, pago manual (pago móvil), sin comisiones.
- Decisión pendiente de implementar: "segunda mano" C2C = usuarios normales
  venden usados SIN tienda (modelo de clasificados + chat), separado del
  flujo de tiendas.
