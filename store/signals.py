from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Carrito, Notificacion, StoreOrder, Usuario, Wallet
from .services.push import send_push_to_user
from .services.realtime import notify_user


@receiver(post_save, sender=Usuario)
def crear_wallet_y_carrito(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(usuario=instance)
        Carrito.objects.get_or_create(usuario=instance)


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
                data={'order_id': instance.id},
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
        data={'order_id': instance.id, 'estado': instance.estado},
    )
