from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from catalogo import views, api_views

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'images/logo_ferreteria_vi.png', permanent=True)),
    path('admin/', admin.site.urls),
    path('', views.lista_productos, name='inicio'),
    path('productos/', views.buscar_productos, name='buscar_productos'),
    path('agregar-carrito/<int:producto_id>/', views.agregar_carrito, name='agregar_carrito'),
    path('actualizar-carrito/<int:producto_id>/', views.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    path('quitar-carrito/<int:producto_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('aplicar-cupon/', views.aplicar_cupon, name='aplicar_cupon'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('historial/', views.historial_compras, name='historial_compras'),
    path('boleta/<int:compra_id>/', views.ver_boleta, name='ver_boleta'),
    path('perfil/', views.mi_perfil, name='mi_perfil'),

    # Detalle de producto, reseñas, favoritos y autocompletado en vivo
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    path('favorito/<int:producto_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('favoritos/', views.mis_favoritos, name='mis_favoritos'),
    path('api/autocompletar/', views.api_autocompletar, name='api_autocompletar'),

    # Evaluación Sumativa 3 (ES3) - Reportes ORM y Formulario de Contacto
    path('reportes/categorias/', views.reporte_categorias, name='reporte_categorias'),
    path('reportes/stock-critico/', views.reporte_stock_critico, name='reporte_stock_critico'),
    path('contacto/', views.contacto_cliente, name='contacto_cliente'),

    # Evaluación Sumativa 4 (ES4) - API REST del Catálogo y Autenticación JWT
    path('api/productos/', api_views.ProductoListCreateAPIView.as_view(), name='api_productos_list_create'),
    path('api/productos/<int:pk>/', api_views.ProductoRetrieveUpdateDestroyAPIView.as_view(), name='api_productos_detail'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Rutas de administración de productos y Dashboard Admin
    path('panel-admin/', views.panel_admin, name='panel_admin'),
    path('panel-admin/despachos/', views.gestion_despachos, name='gestion_despachos'),
    path('panel-admin/actualizar-estado/<int:compra_id>/', views.actualizar_estado_compra, name='actualizar_estado_compra'),
    path('reponer-stock/<int:producto_id>/', views.reponer_stock, name='reponer_stock'),
    path('agregar-producto/', views.agregar_producto, name='agregar_producto'),
    path('editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    
    # Rutas de sesión, registro y recuperación de contraseña por Gmail
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('registrar/', views.registrar_usuario, name='registrar_usuario'),
    path('recuperar-password/', views.recuperar_password, name='recuperar_password'),
    path('logout/', LogoutView.as_view(next_page='inicio'), name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
