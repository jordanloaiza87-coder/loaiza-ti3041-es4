from django.db import models
from django.contrib.auth.models import User

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    precio = models.IntegerField()
    stock = models.IntegerField()
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    imagen_url = models.URLField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"

    @property
    def cuota_6(self):
        cuota = max(1, self.precio // 6)
        return f"{cuota:,}".replace(",", ".")


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    foto = models.ImageField(upload_to='perfiles/', null=True, blank=True)
    foto_url = models.URLField(max_length=500, null=True, blank=True)

    @property
    def avatar_url(self):
        if self.foto:
            try:
                return self.foto.url
            except ValueError:
                pass
        if self.foto_url:
            return self.foto_url
        return None

    def __str__(self):
        return f"Perfil de {self.usuario.username}"

class Carrito(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        return self.producto.precio * self.cantidad

class Compra(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compras')
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.IntegerField(default=0)
    metodo_pago = models.CharField(max_length=60, default='Webpay Plus (Tarjeta Débito/Crédito)')
    cupon_codigo = models.CharField(max_length=40, blank=True, default='')
    descuento = models.IntegerField(default=0)

    ESTADO_CHOICES = [
        ('aprobado', 'Pago Aprobado'),
        ('bodega', 'En Bodega / Preparación'),
        ('en_ruta', 'En Ruta Ocean Drive'),
        ('listo_retiro', 'Listo para Retiro en Tienda'),
        ('entregado', 'Entregado al Cliente'),
    ]
    estado_envio = models.CharField(max_length=30, choices=ESTADO_CHOICES, default='aprobado')

    class Meta:
        ordering = ['-fecha']

    @property
    def is_retiro(self):
        return 'retiro' in (self.metodo_pago or '').lower()

    @property
    def estado_display(self):
        if self.estado_envio == 'listo_retiro':
            return '¡Listo para Retiro en Tienda!'
        if self.is_retiro and self.estado_envio == 'bodega':
            return 'Preparando en Tienda'
        if self.is_retiro and self.estado_envio == 'entregado':
            return 'Retirado por el Cliente'
        return dict(self.ESTADO_CHOICES).get(self.estado_envio, 'Pago Aprobado')

    @property
    def estado_step(self):
        mapping = {
            'aprobado': 1,
            'bodega': 2,
            'en_ruta': 3,
            'listo_retiro': 3,
            'entregado': 4,
        }
        return mapping.get(self.estado_envio, 1)

    @property
    def subtotal_sin_descuento(self):
        return self.total + (self.descuento or 0)

    @property
    def monto_neto(self):
        return int(round(self.total / 1.19))

    @property
    def monto_iva(self):
        return self.total - self.monto_neto

    def __str__(self):
        return f"Compra #{self.id} - {self.usuario.username} (${self.total})"


class Favorito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favoritos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='favoritos')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'producto')
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.usuario.username} ❤ {self.producto.nombre}"


class ResenaProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='resenas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resenas')
    estrellas = models.PositiveSmallIntegerField(default=5)
    comentario = models.TextField(max_length=600)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.producto.nombre} ({self.estrellas}★) por {self.usuario.username}"

class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    nombre_producto = models.CharField(max_length=100)
    categoria_producto = models.CharField(max_length=50, blank=True, default='')
    imagen_url_snapshot = models.CharField(max_length=500, blank=True, default='')
    precio_unitario = models.IntegerField()
    cantidad = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


class ConsultaCliente(models.Model):
    """Modelo para formulario de contacto/consultas de clientes (Evaluación Sumativa 3 - ES3)."""
    nombre = models.CharField(max_length=120, verbose_name="Nombre del Cliente")
    correo = models.EmailField(verbose_name="Correo Electrónico")
    mensaje = models.TextField(verbose_name="Mensaje de Consulta")
    producto_interes = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consultas',
        verbose_name="Producto de Interés (Opcional)"
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Consulta")

    class Meta:
        verbose_name = "Consulta de Cliente"
        verbose_name_plural = "Consultas de Clientes"
        ordering = ['-fecha']

    def __str__(self):
        return f"Consulta de {self.nombre} ({self.correo}) - {self.fecha.strftime('%d/%m/%Y %H:%M')}"
