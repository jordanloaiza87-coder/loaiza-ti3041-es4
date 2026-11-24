from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Producto
from .serializers import ProductoSerializer


class ProductoListCreateAPIView(generics.ListCreateAPIView):
    """
    Endpoint REST: /api/productos/
    - GET (Público): Retorna el listado completo de productos en formato JSON (200 OK).
    - POST (Protegido con JWT): Crea un nuevo producto (201 Created).
      Rechaza datos inválidos con 400 Bad Request y peticiones sin token válido con 401 Unauthorized.
    """
    queryset = Producto.objects.all().order_by('id')
    serializer_class = ProductoSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProductoRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Endpoint REST: /api/productos/<int:pk>/
    - GET (Público): Retorna el detalle de un producto (200 OK) o 404 Not Found si no existe.
    - PUT / PATCH (Protegido con JWT): Actualiza un producto existente (200 OK o 400 Bad Request).
    - DELETE (Protegido con JWT): Elimina un producto existente (204 No Content).
      Sin token JWT válido, las operaciones de escritura responden 401 Unauthorized.
    """
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
