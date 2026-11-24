from django.contrib import admin
from .models import Producto, ConsultaCliente

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'stock', 'imagen')
    search_fields = ('nombre',)
    list_filter = ('categoria',)


@admin.register(ConsultaCliente)
class ConsultaClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'correo', 'producto_interes', 'fecha')
    search_fields = ('nombre', 'correo', 'mensaje')
    list_filter = ('fecha', 'producto_interes')
    readonly_fields = ('fecha',)