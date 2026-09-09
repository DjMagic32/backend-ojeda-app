from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import (
    Carrito,
    DriverProfile,
    InventarioAlmacen,
    MovimientoStock,
    Negocio,
    NegocioMiembro,
    Notificacion,
    ProductoTienda,
    Almacen,
    Sucursal,
    StoreOrder,
    Tienda,
    Usuario,
    Wallet,
)
from .services.push import send_push_to_user
from .services.realtime import notify_user


@receiver(post_save, sender=Usuario)
def crear_wallet_y_carrito(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(usuario=instance)
        Carrito.objects.get_or_create(usuario=instance)


@receiver(post_save, sender=Tienda)
def crear_negocio_y_propietario(sender, instance: Tienda, created, **kwargs):
    """Crea el contexto administrativo al registrar una nueva tienda."""
    if not created:
        return

    negocio, _ = Negocio.objects.get_or_create(
        tienda=instance,
        defaults={'nombre_legal': instance.nombre},
    )
    NegocioMiembro.objects.get_or_create(
        negocio=negocio,
        usuario=instance.usuario,
        defaults={'rol': NegocioMiembro.ROL_PROPIETARIO},
    )


@receiver(post_save, sender=Negocio)
def crear_estructura_principal(sender, instance: Negocio, created, **kwargs):
    """Deja lista una ubicación inicial sin obligar a configurar almacenes aún."""
    if not created:
        return

    sucursal, _ = Sucursal.objects.get_or_create(
        negocio=instance,
        codigo='PRINCIPAL',
        defaults={
            'nombre': 'Principal',
            'direccion': instance.tienda.direccion or '',
        },
    )
    Almacen.objects.get_or_create(
        sucursal=sucursal,
        codigo='PRINCIPAL',
        defaults={'nombre': 'Almacén principal'},
    )


@receiver(post_save, sender=ProductoTienda)
def crear_existencia_inicial(sender, instance: ProductoTienda, created, **kwargs):
    """Asocia el stock inicial de productos al almacén principal.

    Los servicios y los productos sin control de stock no crean existencias.
    """
    if not created or instance.tipo == ProductoTienda.TIPO_SERVICIO or instance.stock is None:
        return

    almacen = (
        Almacen.objects.filter(
            sucursal__negocio__tienda_id=instance.tienda_id,
            sucursal__activo=True,
            activo=True,
            codigo='PRINCIPAL',
        )
        .order_by('id')
        .first()
    )
    if almacen is not None:
        InventarioAlmacen.objects.get_or_create(
            producto=instance,
            almacen=almacen,
            defaults={'cantidad': instance.stock},
        )


@receiver(post_save, sender=Notificacion)
def difundir_notificacion(sender, instance: Notificacion, created, **kwargs):
    """Empuja la notificación al WebSocket del usuario y a su token push.

    Nota: las notificaciones de tipo ``mensaje`` ya disparan push desde la
    vista/consumer del chat para incluir contexto; aquí mandamos WS siempre
    para que la app actualice el badge y feeds en vivo.
    """
    if not created:
        return

    payload = {
        'id': instance.id,
        'titulo': instance.titulo,
        'mensaje': instance.mensaje,
        'tipo': instance.tipo,
        'data': instance.data,
        'leido': instance.leido,
        'creado': instance.creado.isoformat(),
    }
    notify_user(instance.usuario_id, payload)

    if instance.tipo != Notificacion.TIPO_MENSAJE:
        send_push_to_user(
            instance.usuario_id,
            title=instance.titulo,
            body=instance.mensaje or '',
            data={'type': instance.tipo, **(instance.data or {})},
        )


@receiver(pre_save, sender=StoreOrder)
def detectar_cambio_estado_orden(sender, instance: StoreOrder, **kwargs):
    """Marca el estado previo para que post_save sepa si cambió."""
    if not instance.pk:
        instance._estado_previo = None
        return
    try:
        previo = StoreOrder.objects.only('estado').get(pk=instance.pk)
        instance._estado_previo = previo.estado
    except StoreOrder.DoesNotExist:
        instance._estado_previo = None


ESTADO_LABELS = {
    StoreOrder.ESTADO_PENDIENTE: 'pendiente',
    StoreOrder.ESTADO_EN_CURSO: 'en curso',
    StoreOrder.ESTADO_COMPLETADO: 'completada',
    StoreOrder.ESTADO_CANCELADO: 'cancelada',
}


@receiver(post_save, sender=StoreOrder)
def notificar_orden(sender, instance: StoreOrder, created, **kwargs):
    """Crea notificaciones para comprador y vendedor cuando hay cambios."""
    producto = instance.producto
    tienda_user_id = producto.tienda.usuario_id if producto and producto.tienda else None

    if created:
        if tienda_user_id and tienda_user_id != instance.usuario_id:
            Notificacion.objects.create(
                usuario_id=tienda_user_id,
                titulo='Tienes una nueva orden',
                mensaje=f'{instance.cantidad} x {producto.nombre}',
                tipo=Notificacion.TIPO_ORDEN,
                data={'order_id': instance.id, 'view': 'store'},
            )
        return

    estado_previo = getattr(instance, '_estado_previo', None)
    if estado_previo == instance.estado:
        return

    etiqueta = ESTADO_LABELS.get(instance.estado, instance.estado)
    Notificacion.objects.create(
        usuario_id=instance.usuario_id,
        titulo='Estado de tu orden actualizado',
        mensaje=f'Tu orden #{instance.id} ahora está {etiqueta}.',
        tipo=Notificacion.TIPO_ORDEN,
        data={'order_id': instance.id, 'estado': instance.estado, 'view': 'buyer'},
    )


@receiver(post_save, sender=StoreOrder)
def gestionar_stock_orden(sender, instance: StoreOrder, created, **kwargs):
    """Mantiene reservas al cambiar una orden fuera de la mutación GraphQL."""
    if instance.canal != StoreOrder.CANAL_ONLINE:
        return
    if not created and getattr(instance, '_estado_previo', None) == instance.estado:
        return

    from .services.inventario import consumir_reservas_orden, liberar_reservas_orden

    if instance.estado == StoreOrder.ESTADO_COMPLETADO:
        consumir_reservas_orden(instance)
    elif instance.estado == StoreOrder.ESTADO_CANCELADO:
        liberar_reservas_orden(instance)


@receiver(pre_save, sender=DriverProfile)
def detectar_cambio_perfil_conductor(sender, instance: DriverProfile, **kwargs):
    """Guarda el estado previo de is_complete para detectar transiciones."""
    if not instance.pk:
        instance._is_complete_previo = False
        return
    try:
        previo = DriverProfile.objects.select_related('usuario').get(pk=instance.pk)
        instance._is_complete_previo = previo.is_complete
    except DriverProfile.DoesNotExist:
        instance._is_complete_previo = False


@receiver(post_save, sender=DriverProfile)
def notificar_perfil_conductor(sender, instance: DriverProfile, created, **kwargs):
    """Crea notificaciones cuando el conductor termina o le falta el registro."""
    if created and not instance.is_complete:
        Notificacion.objects.create(
            usuario_id=instance.usuario_id,
            titulo='Completa tu perfil de conductor',
            mensaje=(
                'Para empezar a recibir entregas o viajes necesitamos los datos '
                'de tu vehículo, licencia, teléfono y cédula.'
            ),
            tipo=Notificacion.TIPO_GENERAL,
            data={'action': 'driver_profile_setup'},
        )
        return

    previo = getattr(instance, '_is_complete_previo', False)
    if not previo and instance.is_complete:
        Notificacion.objects.create(
            usuario_id=instance.usuario_id,
            titulo='¡Listo! Tu registro de conductor está completo',
            mensaje=(
                'Ya puedes recibir solicitudes de entrega y de taxi. '
                'Activa tu disponibilidad cuando estés listo para trabajar.'
            ),
            tipo=Notificacion.TIPO_GENERAL,
            data={'action': 'driver_profile_completed'},
        )
