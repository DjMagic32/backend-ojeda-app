from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
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
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.nombre} - {self.tienda.nombre}"

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
    def subtotal(self):
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