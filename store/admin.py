from django.contrib import admin
from django.urls import path
from django.http import HttpResponse, HttpResponseRedirect
import csv
from .models import (
    Carrito,
    Categoria,
    Comentario,
    ComentarioProducto,
    Conversation,
    ExpoPushToken,
    ItemCarrito,
    Message,
    MovimientoStock,
    Pedido,
    Producto,
    ProductoTienda,
    Referencia,
    Reporte,
    StoreOrder,
    StoreOrderReview,
    StoreOrderSellerReview,
    Tienda,
    TarifaDelivery,
    Usuario,
    Wallet,
    DriverProfile,
    Lugar,
    ServiceRequest,
    ArticuloUsado,
)
from .analytics.predicciones import realizar_predicciones
from django.contrib import messages


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'rol', 'edad', 'genero', 'telefono', 'cedula_pasaporte', 'ingresos_minimos_mensuales', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'cedula_pasaporte')
    list_filter = ('rol', 'genero', 'is_active', 'is_staff')

@admin.register(Tienda)
class TiendaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'usuario', 'direccion', 'telefono', 'verificada', 'creado')
    search_fields = ('nombre', 'usuario__username')
    list_filter = ('verificada', 'creado')
    list_editable = ('verificada',)

@admin.register(ProductoTienda)
class ProductoTiendaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tienda', 'precio', 'stock')
    search_fields = ('nombre', 'tienda__nombre')
    list_filter = ('tienda',)

@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'creado')
    search_fields = ('usuario__username',)
    list_filter = ('creado',)

@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    list_display = ('carrito', 'producto_tienda', 'cantidad')
    search_fields = ('carrito__usuario__username', 'producto_tienda__nombre')
    list_filter = ('carrito',)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'es_comida', 'descripcion')
    search_fields = ('nombre',)
    list_filter = ('tipo', 'es_comida')

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'stock')
    search_fields = ('nombre', 'categoria__nombre')
    list_filter = ('categoria',)

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tienda', 'calificacion', 'creado')
    search_fields = ('usuario__username', 'tienda__nombre')
    list_filter = ('calificacion', 'creado')

@admin.register(ComentarioProducto)
class ComentarioProductoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'producto', 'creado')
    search_fields = ('usuario__username', 'producto__nombre')
    list_filter = ('creado',)

@admin.register(Referencia)
class ReferenciaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tienda', 'producto', 'es_mal_comprador', 'es_mal_vendedor', 'creado')
    search_fields = ('usuario__username', 'tienda__nombre', 'producto__nombre')
    list_filter = ('es_mal_comprador', 'es_mal_vendedor', 'creado')

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'saldo', 'actualizado')
    search_fields = ('usuario__username',)
    list_filter = ('actualizado',)

class PedidoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tienda', 'total', 'creado', 'pagado')
    search_fields = ('usuario__username', 'tienda__nombre')
    list_filter = ('creado', 'pagado')
    change_list_template = "admin/analytics_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export/', self.admin_site.admin_view(self.export_analytics), name='store_pedido_export'),
            path('predicciones/', self.admin_site.admin_view(self.ver_predicciones), name='store_pedido_predicciones'),
            ]
        
        return custom_urls + urls

    def export_analytics(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="analytics.csv"'

        writer = csv.writer(response)
        writer.writerow(['Tienda', 'Producto', 'Ventas', 'Mes', 'Comprador', 'Género', 'Ingresos Mínimos'])

        pedidos = Pedido.objects.all()
        for pedido in pedidos:
            for item in pedido.items.all():
                writer.writerow([
                    pedido.tienda.nombre,
                    item.producto.nombre,
                    item.cantidad,
                    pedido.creado.strftime('%Y-%m'),
                    pedido.usuario.username,
                    pedido.usuario.genero,
                    pedido.usuario.ingresos_minimos_mensuales
                ])

        return response

    def ver_predicciones(self, request):
        predicciones, y_test = realizar_predicciones()
        if not predicciones or not y_test:  # Verificar si los resultados están vacíos
            messages.warning(request, "No hay datos suficientes para realizar predicciones.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="predicciones.csv"'

        writer = csv.writer(response)
        writer.writerow(['Predicción', 'Real'])

        for prediccion, real in zip(predicciones, y_test):
            writer.writerow([prediccion, real])

        return response


admin.site.register(Pedido, PedidoAdmin)


@admin.register(StoreOrder)
class StoreOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'producto', 'cantidad', 'estado', 'creado')
    search_fields = ('usuario__username', 'producto__nombre')
    list_filter = ('estado', 'creado')


@admin.register(StoreOrderReview)
class StoreOrderReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'producto', 'usuario', 'rating', 'creado')
    search_fields = ('producto__nombre', 'usuario__username', 'order__id')
    list_filter = ('rating', 'creado')


@admin.register(StoreOrderSellerReview)
class StoreOrderSellerReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'tienda', 'comprador', 'rating', 'creado')
    search_fields = ('tienda__nombre', 'comprador__username', 'order__id')
    list_filter = ('rating', 'creado')


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'estado', 'vehiculo_tipo', 'vehiculo_placa', 'actualizado')
    search_fields = ('usuario__username', 'vehiculo_placa', 'licencia_numero')
    list_filter = ('estado', 'vehiculo_tipo')


@admin.register(Lugar)
class LugarAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'direccion', 'lat', 'lng', 'activo', 'actualizado')
    search_fields = ('nombre', 'alias', 'direccion')
    list_filter = ('categoria', 'activo')
    list_editable = ('activo',)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'producto', 'creado', 'actualizado')
    search_fields = ('participantes__email',)
    list_filter = ('creado',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'autor', 'leido', 'creado')
    search_fields = ('autor__email', 'contenido')
    list_filter = ('leido', 'creado')


@admin.register(ExpoPushToken)
class ExpoPushTokenAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'plataforma', 'creado', 'actualizado')
    search_fields = ('usuario__email', 'token')


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'tipo',
        'estado',
        'cliente',
        'driver',
        'store_order',
        'creado',
    )
    search_fields = ('cliente__username', 'driver__username', 'store_order__id')
    list_filter = ('tipo', 'estado', 'creado')

@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ('id', 'reportante', 'tienda', 'producto', 'motivo', 'estado', 'creado')
    search_fields = ('reportante__email', 'tienda__nombre', 'producto__nombre')
    list_filter = ('motivo', 'estado', 'creado')
    list_editable = ('estado',)


@admin.register(TarifaDelivery)
class TarifaDeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'tarifa_base', 'tarifa_por_km', 'costo_minimo', 'activa', 'actualizado')
    list_editable = ('tarifa_base', 'tarifa_por_km', 'costo_minimo', 'activa')


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ('id', 'producto', 'tipo', 'cantidad', 'stock_resultante', 'origen', 'order', 'creado')
    search_fields = ('producto__nombre', 'producto__tienda__nombre')
    list_filter = ('tipo', 'origen', 'creado')
    readonly_fields = ('producto', 'tipo', 'cantidad', 'stock_resultante', 'origen', 'order', 'creado')

    def has_add_permission(self, request):
        return False


@admin.register(ArticuloUsado)
class ArticuloUsadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'vendedor', 'precio', 'moneda', 'estado_articulo', 'activo', 'creado')
    search_fields = ('titulo', 'descripcion', 'vendedor__username', 'vendedor__email')
    list_filter = ('moneda', 'estado_articulo', 'activo', 'creado')
    list_editable = ('activo',)
