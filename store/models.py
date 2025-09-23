from decimal import Decimal

from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] 
    ES_TIENDA = 'TIENDA'
    ES_CLIENTE = 'CLIENTE'
    ROLES = [
        (ES_TIENDA, 'Tienda'),
        (ES_CLIENTE, 'Cliente'),
    ]

    GENERO_MASCULINO = 'M'
    GENERO_FEMENINO = 'F'
    GENERO_OTRO = 'O'
    GENEROS = [
        (GENERO_MASCULINO, 'Masculino'),
        (GENERO_FEMENINO, 'Femenino'),
        (GENERO_OTRO, 'Otro'),
    ]
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=10, choices=ROLES, default=ES_CLIENTE)
    edad = models.PositiveIntegerField(blank=True, null=True)
    genero = models.CharField(max_length=1, choices=GENEROS, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    cedula_pasaporte = models.CharField(max_length=20, unique=True, blank=True, null=True)
    foto_identificacion = models.ImageField(upload_to='identificaciones/', blank=True, null=True)
    ingresos_minimos_mensuales = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.rol})"

class Tienda(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': Usuario.ES_TIENDA})
    nombre = models.CharField(max_length=200)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    informacion_fiscal = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class ProductoTienda(models.Model):
    TIPO_PRODUCTO = 'PRODUCTO'
    TIPO_SERVICIO = 'SERVICIO'
    TIPOS = [
        (TIPO_PRODUCTO, 'Producto'),
        (TIPO_SERVICIO, 'Servicio'),
    ]

    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(blank=True, null=True)
    tipo = models.CharField(max_length=15, choices=TIPOS, default=TIPO_PRODUCTO)
    imagen = models.ImageField(upload_to='productos_tienda/', blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} - {self.tienda.nombre} ({self.tipo})"


class StoreOrder(models.Model):
    ESTADO_PENDIENTE = 'pending'
    ESTADO_EN_CURSO = 'ongoing'
    ESTADO_COMPLETADO = 'completed'
    ESTADO_CANCELADO = 'cancelled'

    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_EN_CURSO, 'En curso'),
        (ESTADO_COMPLETADO, 'Completado'),
        (ESTADO_CANCELADO, 'Cancelado'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='store_orders')
    producto = models.ForeignKey(ProductoTienda, on_delete=models.CASCADE, related_name='orders')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    direccion_entrega = models.CharField(max_length=255, blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f"Orden #{self.id} - {self.usuario.email} -> {self.producto.nombre}"

class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrito de {self.usuario.username}"

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    @property
    def subtotal(self) -> Decimal:
        return self.cantidad * self.producto.precio

class Pedido(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='pedidos')
    items = models.ManyToManyField(ItemCarrito)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    creado = models.DateTimeField(auto_now_add=True)
    pagado = models.BooleanField(default=False)

    def __str__(self):
        return f"Pedido {self.id} de {self.usuario.username}"

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)

    def __str__(self):
        return self.nombre

class Comentario(models.Model):
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='comentarios')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    contenido = models.TextField()
    calificacion = models.PositiveSmallIntegerField(default=5)  # Rango de 1 a 5 estrellas
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.tienda.nombre}: {self.calificacion} estrellas"

class ComentarioProducto(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    texto = models.TextField()
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comentario de {self.usuario.username} en {self.producto.nombre}"

class Referencia(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='referencias')
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='referencias', blank=True, null=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='referencias', blank=True, null=True)
    es_mal_comprador = models.BooleanField(default=False)
    es_mal_vendedor = models.BooleanField(default=False)
    comentario = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Referencia de {self.usuario.username}"

class Wallet(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='wallet')
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet de {self.usuario.username} - Saldo: {self.saldo}"
