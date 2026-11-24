from rest_framework import serializers
from .models import Producto


class ProductoSerializer(serializers.ModelSerializer):
    """
    Serializer del modelo principal Producto (Evaluación Sumativa 4 - ES4).
    Incluye validaciones de negocio para rechazar datos inválidos con código HTTP 400.
    """

    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'categoria', 'precio', 'stock', 'imagen', 'imagen_url']
        read_only_fields = ['id']

    def validate_nombre(self, value):
        nombre = (value or '').strip()
        if len(nombre) < 2:
            raise serializers.ValidationError(
                "El nombre del producto es obligatorio y debe tener al menos 2 caracteres."
            )
        return nombre

    def validate_categoria(self, value):
        categoria = (value or '').strip()
        if len(categoria) < 2:
            raise serializers.ValidationError(
                "La categoría es obligatoria y debe tener al menos 2 caracteres."
            )
        return categoria

    def validate_precio(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(
                "El precio debe ser un valor entero positivo mayor que 0."
            )
        return value

    def validate_stock(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError(
                "El stock disponible no puede ser un número negativo."
            )
        return value
