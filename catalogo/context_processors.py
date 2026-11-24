from .models import Producto, Favorito
from .views import obtener_cantidad_carrito

def navbar_context(request):
    """
    Context processor para proveer variables globales consistentes a todas las páginas:
    - nav_categorias: lista de categorías únicas para el dropdown del buscador del navbar
    - cart_count: cantidad total de productos en el carrito (0 para admin)
    - fav_count: cantidad total de favoritos (0 para admin)
    - ultimos_visitados_productos: lista de hasta 3 productos visitados en la sesión (ES3)
    - contador_visitas_sesion: cantidad de páginas visitadas en la sesión activa (ES3)
    """
    try:
        nav_categorias = sorted([
            c for c in Producto.objects.values_list('categoria', flat=True).distinct() if c
        ])
    except Exception:
        nav_categorias = []

    # Funcionalidad con sesiones (ES3 - Criterio 2.1.4): Últimos 3 productos visitados y contador
    ultimos_visitados_productos = []
    contador_visitas_sesion = 1
    try:
        contador_visitas_sesion = request.session.get('contador_visitas', 0) + 1
        request.session['contador_visitas'] = contador_visitas_sesion
        
        ultimos_ids = request.session.get('ultimos_visitados', [])
        if ultimos_ids:
            id_map = {p.id: p for p in Producto.objects.filter(id__in=ultimos_ids)}
            ultimos_visitados_productos = [id_map[pid] for pid in ultimos_ids if pid in id_map]
    except Exception:
        pass

    # El administrador nunca tiene carrito ni favoritos
    if request.user.is_authenticated and request.user.is_superuser:
        return {
            'nav_categorias': nav_categorias,
            'cart_count': 0,
            'fav_count': 0,
            'ultimos_visitados_productos': ultimos_visitados_productos,
            'contador_visitas_sesion': contador_visitas_sesion,
        }

    try:
        cart_count = obtener_cantidad_carrito(request)
    except Exception:
        cart_count = 0

    try:
        if request.user.is_authenticated:
            fav_count = Favorito.objects.filter(usuario=request.user).count()
        else:
            fav_count = 0
    except Exception:
        fav_count = 0

    return {
        'nav_categorias': nav_categorias,
        'cart_count': cart_count,
        'fav_count': fav_count,
        'ultimos_visitados_productos': ultimos_visitados_productos,
        'contador_visitas_sesion': contador_visitas_sesion,
    }
