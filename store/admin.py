from django.contrib import admin
from django.urls import path
from django.http import HttpResponse, HttpResponseRedirect
import csv
from .models import Usuario, Tienda, ProductoTienda, Carrito, ItemCarrito, Pedido, Categoria, Producto, Comentario, ComentarioProducto, Referencia, Wallet
from .analytics.predicciones import realizar_predicciones
from django.contrib import messages


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'rol', 'edad', 'genero', 'telefono', 'cedula_pasaporte', 'ingresos_minimos_mensuales', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'cedula_pasaporte')
    list_filter = ('rol', 'genero', 'is_active', 'is_staff')

@admin.register(Tienda)
class TiendaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'usuario', 'direccion', 'telefono', 'creado')
    search_fields = ('nombre', 'usuario__username')
    list_filter = ('creado',)

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
    list_display = ('carrito', 'producto', 'cantidad')
    search_fields = ('carrito__usuario__username', 'producto__nombre')
    list_filter = ('carrito',)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

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