import random
import unicodedata
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth import update_session_auth_hash, login as auth_login
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Sum, Avg, Count, Min, Max
from django import forms
from .models import Producto, PerfilUsuario, Carrito, ItemCarrito, Compra, DetalleCompra, Favorito, ResenaProducto, ConsultaCliente
from .forms import ProductoForm, ConsultaClienteForm


CUPONES_DISPONIBLES = {
    'VICECITY10': {'tipo': 'porcentaje', 'valor': 10, 'etiqueta': '10% DCTO Vice City'},
    'FERRETERIA20': {'tipo': 'porcentaje', 'valor': 20, 'etiqueta': '20% DCTO Pro'},
    'GTA6VIP': {'tipo': 'porcentaje', 'valor': 15, 'etiqueta': '15% DCTO VIP'},
    'ENVIOGRATIS': {'tipo': 'fijo', 'valor': 3000, 'etiqueta': '$3.000 Bono Despacho'},
}


def calcular_descuento_cupon(subtotal, codigo_cupon):
    """Calcula el descuento y total final según el cupón activo."""
    codigo = (codigo_cupon or '').strip().upper()
    if subtotal <= 0 or codigo not in CUPONES_DISPONIBLES:
        return 0, max(0, subtotal), None
    info = CUPONES_DISPONIBLES[codigo]
    if info['tipo'] == 'porcentaje':
        descuento = int(round(subtotal * (info['valor'] / 100.0)))
    else:
        descuento = min(subtotal, info['valor'])
    total_final = max(0, subtotal - descuento)
    return descuento, total_final, {'codigo': codigo, **info}


def obtener_ids_favoritos(request):
    """Devuelve el conjunto de IDs de productos marcados como favoritos (usuario o invitado)."""
    fav_invitado = set()
    for pid in request.session.get('favoritos_invitado', []):
        try:
            fav_invitado.add(int(pid))
        except (ValueError, TypeError):
            continue

    if request.user.is_authenticated:
        if fav_invitado:
            for pid in fav_invitado:
                if Producto.objects.filter(id=pid).exists():
                    Favorito.objects.get_or_create(usuario=request.user, producto_id=pid)
            request.session.pop('favoritos_invitado', None)
            request.session.modified = True
        return set(Favorito.objects.filter(usuario=request.user).values_list('producto_id', flat=True))
    return fav_invitado


def sincronizar_carrito_invitado(request, user=None):
    """Transfiere los productos guardados en la sesión de invitado al Carrito en BD del usuario."""
    target_user = user or request.user
    if not target_user or not target_user.is_authenticated:
        return False

    PerfilUsuario.objects.get_or_create(usuario=target_user)

    carrito_invitado = request.session.get('carrito_invitado', {})
    if not carrito_invitado:
        return False

    carrito, _ = Carrito.objects.get_or_create(usuario=target_user)
    tenia_items = False

    for pid_str, cant in list(carrito_invitado.items()):
        try:
            producto = Producto.objects.get(id=int(pid_str))
            cantidad = int(cant)
            if producto.stock > 0 and cantidad > 0:
                item, creado = ItemCarrito.objects.get_or_create(carrito=carrito, producto=producto)
                if not creado:
                    item.cantidad = min(item.cantidad + cantidad, producto.stock)
                else:
                    item.cantidad = min(cantidad, producto.stock)
                item.save()
                tenia_items = True
        except (Producto.DoesNotExist, ValueError):
            continue

    del request.session['carrito_invitado']
    request.session.modified = True
    return tenia_items


@receiver(user_logged_in)
def al_iniciar_sesion(sender, request, user, **kwargs):
    """Al iniciar sesión, fusiona automáticamente el carrito guardado en sesión."""
    PerfilUsuario.objects.get_or_create(usuario=user)
    if request.session.get('carrito_invitado'):
        request.session['redirigir_a_carrito'] = True
        sincronizar_carrito_invitado(request, user=user)


class CustomLoginView(LoginView):
    template_name = 'catalogo/login.html'

    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        if self.request.session.pop('redirigir_a_carrito', False):
            return reverse('ver_carrito')
        return reverse('inicio')


def obtener_cantidad_carrito(request):
    """Devuelve el total de unidades actualmente en el carrito (de usuario o invitado)."""
    if request.user.is_authenticated:
        sincronizar_carrito_invitado(request)
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        return sum(i.cantidad for i in ItemCarrito.objects.filter(carrito=carrito))
    else:
        carrito_invitado = request.session.get('carrito_invitado', {})
        return sum(int(c) for c in carrito_invitado.values())


def _normalizar_texto(texto):
    """Elimina tildes y pasa a minúsculas para búsquedas flexibles."""
    if not texto:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()


def lista_productos(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        sincronizar_carrito_invitado(request)
        compras_usuario = Compra.objects.filter(usuario=request.user).prefetch_related('detalles')[:5]
    else:
        compras_usuario = []

    q = request.GET.get('q', '').strip()
    if q:
        return redirect(f"{reverse('buscar_productos')}?q={q}")

    productos = list(Producto.objects.all())
    cart_count = obtener_cantidad_carrito(request)

    # 1. Producto Más Vendido (según DetalleCompra real o el de mayor rotación)
    ventas_por_producto = (
        DetalleCompra.objects.exclude(producto__isnull=True)
        .values('producto_id')
        .annotate(total_vendido=Sum('cantidad'))
        .order_by('-total_vendido')
    )
    producto_mas_vendido = None
    unidades_mas_vendido = 0
    if ventas_por_producto:
        top_entry = ventas_por_producto[0]
        producto_mas_vendido = Producto.objects.filter(id=top_entry['producto_id']).first()
        unidades_mas_vendido = top_entry['total_vendido'] or 0

    if not producto_mas_vendido and productos:
        producto_mas_vendido = next((p for p in productos if 'taladro' in p.nombre.lower()), productos[0])
        unidades_mas_vendido = 48

    # 2. Producto Favorito de la Comunidad (Insignia de alta gama / mejor valorado)
    productos_por_precio = sorted(productos, key=lambda x: x.precio, reverse=True)
    producto_favorito = productos_por_precio[0] if productos_por_precio else None

    # 3. Productos que Más Destacan (Top 4 destacados de distintas categorías)
    productos_destacados = productos_por_precio[:4]

    # 4. Productos de Último Momento (Recién agregados al catálogo)
    ultimos_productos = sorted(productos, key=lambda x: x.id, reverse=True)[:4]

    # 5. Información Pura por Categoría (con todos los productos de cada categoría)
    mapa_categorias = {}
    for p in productos:
        cat_nombre = (p.categoria or 'General').strip()
        if cat_nombre not in mapa_categorias:
            mapa_categorias[cat_nombre] = []
        mapa_categorias[cat_nombre].append(p)

    categorias_info = []
    for cat_nombre, items_cat in mapa_categorias.items():
        precios = [x.precio for x in items_cat]
        producto_estrella = max(items_cat, key=lambda x: x.precio)
        categorias_info.append({
            'nombre': cat_nombre,
            'total_productos': len(items_cat),
            'stock_total': sum(x.stock for x in items_cat),
            'precio_min': min(precios) if precios else 0,
            'precio_max': max(precios) if precios else 0,
            'producto_estrella': producto_estrella,
            'productos': items_cat,
        })

    favoritos_ids = obtener_ids_favoritos(request)
    return render(request, 'catalogo/index.html', {
        'productos': productos,
        'compras_usuario': compras_usuario,
        'cart_count': cart_count,
        'favoritos_ids': favoritos_ids,
        'fav_count': len(favoritos_ids),
        'search_query': q,
        'producto_mas_vendido': producto_mas_vendido,
        'unidades_mas_vendido': unidades_mas_vendido,
        'producto_favorito': producto_favorito,
        'productos_destacados': productos_destacados,
        'ultimos_productos': ultimos_productos,
        'categorias_info': categorias_info,
    })


def buscar_productos(request):
    """Página dedicada de resultados de búsqueda y catálogo con barra lateral de filtros (estilo Mercado Libre / GTA VI)."""
    if request.user.is_authenticated:
        sincronizar_carrito_invitado(request)

    q = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    orden = request.GET.get('orden', 'relevantes').strip()
    disponibles = request.GET.get('disponibles', '') == '1'
    destacados = request.GET.get('destacados', '') == '1'
    max_precio_str = request.GET.get('max_precio', '').strip()
    max_precio = None
    if max_precio_str.isdigit():
        max_precio = int(max_precio_str)

    todos_los_productos = list(Producto.objects.all())

    # Mapa de ventas para ordenar por "mas_vendidos"
    ventas_qs = (
        DetalleCompra.objects.exclude(producto__isnull=True)
        .values('producto_id')
        .annotate(total_vendido=Sum('cantidad'))
    )
    mapa_ventas = {row['producto_id']: (row['total_vendido'] or 0) for row in ventas_qs}

    # Agrupar categorías para el sidebar izquierdo
    conteo_categorias = {}
    for p in todos_los_productos:
        cat_name = (p.categoria or 'General').strip()
        conteo_categorias[cat_name] = conteo_categorias.get(cat_name, 0) + 1

    categorias_sidebar = [
        {'nombre': nombre, 'total': total}
        for nombre, total in sorted(conteo_categorias.items(), key=lambda x: x[0])
    ]

    # Filtrar productos según parámetros seleccionados
    q_norm = _normalizar_texto(q)
    cat_norm = _normalizar_texto(categoria)

    productos_filtrados = []
    for p in todos_los_productos:
        if q_norm:
            if q_norm not in _normalizar_texto(p.nombre) and q_norm not in _normalizar_texto(p.categoria):
                continue
        if cat_norm and cat_norm != 'all':
            if _normalizar_texto(p.categoria) != cat_norm:
                continue
        if disponibles and p.stock <= 0:
            continue
        if max_precio is not None and p.precio > max_precio:
            continue
        if destacados and p.precio < 8000:
            continue
        productos_filtrados.append(p)

    # Ordenar resultados
    if orden == 'ultimo_momento':
        productos_filtrados.sort(key=lambda x: x.id, reverse=True)
    elif orden == 'mas_vendidos':
        productos_filtrados.sort(key=lambda x: (mapa_ventas.get(x.id, 0), x.precio), reverse=True)
    elif orden == 'mayor_precio':
        productos_filtrados.sort(key=lambda x: x.precio, reverse=True)
    elif orden == 'menor_precio':
        productos_filtrados.sort(key=lambda x: x.precio)

    # Título dinámico de la búsqueda / categoría
    if q and categoria:
        titulo_busqueda = f'{q} en {categoria}'
    elif q:
        titulo_busqueda = q.capitalize()
    elif categoria:
        titulo_busqueda = categoria
    elif orden == 'mas_vendidos':
        titulo_busqueda = 'Más Vendidos'
    elif orden == 'ultimo_momento':
        titulo_busqueda = 'De Último Momento'
    elif max_precio:
        titulo_busqueda = f'Menos de ${max_precio}'
    elif destacados:
        titulo_busqueda = 'Productos Destacados'
    else:
        titulo_busqueda = 'Todos los Productos'

    cart_count = obtener_cantidad_carrito(request)
    favoritos_ids = obtener_ids_favoritos(request)

    return render(request, 'catalogo/productos.html', {
        'productos': productos_filtrados,
        'total_resultados': len(productos_filtrados),
        'total_catalogo': len(todos_los_productos),
        'search_query': q,
        'categoria_actual': categoria,
        'orden_actual': orden,
        'disponibles_activo': disponibles,
        'destacados_activo': destacados,
        'max_precio_actual': max_precio,
        'titulo_busqueda': titulo_busqueda,
        'categorias_sidebar': categorias_sidebar,
        'cart_count': cart_count,
        'favoritos_ids': favoritos_ids,
        'fav_count': len(favoritos_ids),
    })


@login_required
def mi_perfil(request):
    """Permite al usuario ver su perfil y cambiar su nombre de usuario, contraseña o foto (por archivo o URL)."""
    sincronizar_carrito_invitado(request)
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)
    mensaje_exito = None
    mensaje_error = None

    if request.method == 'POST':
        nuevo_username = request.POST.get('username', '').strip()
        foto_url = request.POST.get('foto_url', '').strip()
        foto_archivo = request.FILES.get('foto')
        quitar_foto = request.POST.get('quitar_foto') == '1'
        nueva_password = request.POST.get('nueva_password', '').strip()
        confirmar_password = request.POST.get('confirmar_password', '').strip()

        # 1. Validar y actualizar nombre de usuario
        if nuevo_username and nuevo_username != request.user.username:
            if User.objects.filter(username=nuevo_username).exclude(pk=request.user.pk).exists():
                mensaje_error = "Ese nombre de usuario ya está en uso por otra cuenta."
            else:
                request.user.username = nuevo_username
                request.user.save()

        # 2. Validar y actualizar contraseña (si el usuario escribió una nueva)
        if not mensaje_error and (nueva_password or confirmar_password):
            if nueva_password != confirmar_password:
                mensaje_error = "Las contraseñas nuevas no coinciden."
            elif len(nueva_password) < 4:
                mensaje_error = "La nueva contraseña debe tener al menos 4 caracteres."
            else:
                request.user.set_password(nueva_password)
                request.user.save()
                update_session_auth_hash(request, request.user)

        # 3. Actualizar foto de perfil (por archivo descargado o por URL)
        if not mensaje_error:
            if quitar_foto:
                perfil.foto = None
                perfil.foto_url = ''
            else:
                if foto_archivo:
                    perfil.foto = foto_archivo
                if foto_url != (perfil.foto_url or ''):
                    perfil.foto_url = foto_url
                    if foto_url and not foto_archivo:
                        perfil.foto = None
            perfil.save()
            mensaje_exito = "¡Los datos de tu perfil han sido actualizados con éxito!"

    total_compras = Compra.objects.filter(usuario=request.user).count() if not request.user.is_superuser else 0
    cart_count = obtener_cantidad_carrito(request)
    return render(request, 'catalogo/perfil.html', {
        'perfil': perfil,
        'mensaje_exito': mensaje_exito,
        'mensaje_error': mensaje_error,
        'total_compras': total_compras,
        'cart_count': cart_count,
    })


def agregar_carrito(request, producto_id):
    """Permite agregar productos al carrito tanto a usuarios autenticados como invitados (soporta AJAX sin recargar)."""
    producto = get_object_or_404(Producto, id=producto_id)
    try:
        cantidad = max(1, int(request.POST.get('cantidad', 1)))
    except ValueError:
        cantidad = 1

    agregado = False
    if producto.stock >= cantidad:
        agregado = True
        if request.user.is_authenticated:
            sincronizar_carrito_invitado(request)
            carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
            item, item_creado = ItemCarrito.objects.get_or_create(carrito=carrito, producto=producto)
            if not item_creado:
                item.cantidad = min(item.cantidad + cantidad, producto.stock)
            else:
                item.cantidad = cantidad
            item.save()
        else:
            carrito_invitado = request.session.get('carrito_invitado', {})
            pid_str = str(producto.id)
            actual = int(carrito_invitado.get(pid_str, 0))
            carrito_invitado[pid_str] = min(actual + cantidad, producto.stock)
            request.session['carrito_invitado'] = carrito_invitado
            request.session.modified = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_count = obtener_cantidad_carrito(request)
        return JsonResponse({
            'ok': agregado,
            'cart_count': cart_count,
            'producto_nombre': producto.nombre,
            'cantidad': cantidad,
        })

    return redirect('inicio')


def eliminar_del_carrito(request, producto_id):
    """Permite quitar un producto del carrito (autenticado o invitado)."""
    if request.user.is_authenticated:
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        ItemCarrito.objects.filter(carrito=carrito, producto_id=producto_id).delete()
    else:
        carrito_invitado = request.session.get('carrito_invitado', {})
        pid_str = str(producto_id)
        if pid_str in carrito_invitado:
            del carrito_invitado[pid_str]
            request.session['carrito_invitado'] = carrito_invitado
            request.session.modified = True
    return redirect('ver_carrito')


def actualizar_cantidad_carrito(request, producto_id):
    """Permite sumar (+), restar (-) o cambiar la cantidad directamente en el carrito (soporta AJAX)."""
    producto = get_object_or_404(Producto, id=producto_id)
    accion = request.POST.get('accion', '').strip()
    cantidad_directa = request.POST.get('cantidad', '').strip()

    nueva_cantidad = 0
    eliminado = False

    if request.user.is_authenticated:
        sincronizar_carrito_invitado(request)
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        item = ItemCarrito.objects.filter(carrito=carrito, producto=producto).first()
        actual = item.cantidad if item else 0

        if accion == 'sumar':
            nueva_cantidad = min(actual + 1, max(1, producto.stock))
        elif accion == 'restar':
            nueva_cantidad = actual - 1
        elif cantidad_directa.isdigit():
            nueva_cantidad = min(int(cantidad_directa), max(1, producto.stock))
        else:
            nueva_cantidad = actual

        if nueva_cantidad <= 0:
            if item:
                item.delete()
            nueva_cantidad = 0
            eliminado = True
        else:
            if not item:
                item = ItemCarrito(carrito=carrito, producto=producto, cantidad=nueva_cantidad)
            else:
                item.cantidad = nueva_cantidad
            item.save()

        items_actuales = list(ItemCarrito.objects.filter(carrito=carrito).select_related('producto'))
        subtotal_carrito = sum(i.subtotal for i in items_actuales)
        cart_count = sum(i.cantidad for i in items_actuales)
    else:
        carrito_invitado = request.session.get('carrito_invitado', {})
        pid_str = str(producto.id)
        actual = int(carrito_invitado.get(pid_str, 0))

        if accion == 'sumar':
            nueva_cantidad = min(actual + 1, max(1, producto.stock))
        elif accion == 'restar':
            nueva_cantidad = actual - 1
        elif cantidad_directa.isdigit():
            nueva_cantidad = min(int(cantidad_directa), max(1, producto.stock))
        else:
            nueva_cantidad = actual

        if nueva_cantidad <= 0:
            carrito_invitado.pop(pid_str, None)
            nueva_cantidad = 0
            eliminado = True
        else:
            carrito_invitado[pid_str] = nueva_cantidad
        request.session['carrito_invitado'] = carrito_invitado
        request.session.modified = True

        subtotal_carrito = 0
        cart_count = 0
        for k_pid, k_cant in carrito_invitado.items():
            try:
                p_obj = Producto.objects.get(id=int(k_pid))
                subtotal_carrito += p_obj.precio * int(k_cant)
                cart_count += int(k_cant)
            except (Producto.DoesNotExist, ValueError):
                continue

    cupon_codigo = request.session.get('cupon_activo', '')
    descuento, total_final, info_cupon = calcular_descuento_cupon(subtotal_carrito, cupon_codigo)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'producto_id': producto.id,
            'cantidad': nueva_cantidad,
            'eliminado': eliminado,
            'stock_max': producto.stock,
            'item_subtotal': producto.precio * nueva_cantidad,
            'subtotal_carrito': subtotal_carrito,
            'descuento': descuento,
            'total_carrito': total_final,
            'cart_count': cart_count,
            'cupon_activo': info_cupon['codigo'] if info_cupon else '',
        })

    return redirect('ver_carrito')


def aplicar_cupon(request):
    """Aplica o quita un cupón promocional en el carrito."""
    if request.method == 'POST':
        accion = request.POST.get('accion', 'aplicar')
        if accion == 'quitar':
            request.session.pop('cupon_activo', None)
            request.session.modified = True
            mensaje = "Cupón eliminado."
            ok = True
        else:
            codigo = (request.POST.get('codigo_cupon') or '').strip().upper()
            if codigo in CUPONES_DISPONIBLES:
                request.session['cupon_activo'] = codigo
                request.session.modified = True
                info = CUPONES_DISPONIBLES[codigo]
                mensaje = f"¡Cupón {codigo} ({info['etiqueta']}) aplicado con éxito!"
                ok = True
            else:
                mensaje = "Cupón no válido. Prueba con VICECITY10, FERRETERIA20, GTA6VIP o ENVIOGRATIS."
                ok = False

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': ok, 'mensaje': mensaje, 'cupon': request.session.get('cupon_activo', '')})

        request.session['cupon_feedback'] = {'ok': ok, 'mensaje': mensaje}
    return redirect('ver_carrito')


class ItemInvitado:
    """Estructura auxiliar para representar items del carrito en sesión igual que ItemCarrito."""
    def __init__(self, producto, cantidad):
        self.producto = producto
        self.cantidad = cantidad

    @property
    def subtotal(self):
        return self.producto.precio * self.cantidad


def ver_carrito(request):
    """Muestra el carrito guardado (en sesión o BD), aplica cupones y procesa la compra con método de pago."""
    if request.user.is_authenticated and request.user.is_superuser:
        messages.info(request, "Los administradores gestionan el inventario y despachos desde el Panel.")
        return redirect('panel_admin')

    cupon_feedback = request.session.pop('cupon_feedback', None)
    cupon_session = request.session.get('cupon_activo', '')

    if request.user.is_authenticated:
        sincronizar_carrito_invitado(request)
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        items_qs = ItemCarrito.objects.filter(carrito=carrito).select_related('producto')

        if request.method == 'POST':
            if request.user.is_superuser:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'error': 'Los administradores no pueden realizar compras.'}, status=403)
                return redirect('ver_carrito')

            if not items_qs.exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'error': 'El carrito está vacío.'}, status=400)
                return redirect('ver_carrito')

            metodo_pago = (request.POST.get('metodo_pago') or 'Webpay Plus (Tarjeta Débito/Crédito)').strip()
            subtotal_compra = 0
            detalles_a_crear = []

            for item in items_qs:
                cant_real = min(item.cantidad, item.producto.stock)
                if cant_real > 0:
                    item.producto.stock -= cant_real
                    item.producto.save()
                    subtotal = item.producto.precio * cant_real
                    subtotal_compra += subtotal

                    img_url = ''
                    if item.producto.imagen:
                        img_url = item.producto.imagen.url
                    elif item.producto.imagen_url:
                        img_url = item.producto.imagen_url

                    detalles_a_crear.append({
                        'producto': item.producto,
                        'nombre_producto': item.producto.nombre,
                        'categoria_producto': item.producto.categoria,
                        'imagen_url_snapshot': img_url,
                        'precio_unitario': item.producto.precio,
                        'cantidad': cant_real,
                    })

            descuento_aplicado, total_compra_final, info_cupon = calcular_descuento_cupon(subtotal_compra, cupon_session)

            compra = Compra.objects.create(
                usuario=request.user,
                total=total_compra_final,
                metodo_pago=metodo_pago,
                cupon_codigo=info_cupon['codigo'] if info_cupon else '',
                descuento=descuento_aplicado,
            )
            for det in detalles_a_crear:
                DetalleCompra.objects.create(compra=compra, **det)

            items_qs.delete()
            request.session.pop('cupon_activo', None)
            request.session.modified = True

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True,
                    'compra_id': compra.id,
                    'total': compra.total,
                    'metodo_pago': compra.metodo_pago,
                    'descuento': compra.descuento,
                    'boleta_url': reverse('ver_boleta', args=[compra.id]),
                    'historial_url': reverse('historial_compras'),
                })

            compras_recientes = Compra.objects.filter(usuario=request.user).prefetch_related('detalles')[:5]
            return render(request, 'catalogo/carrito.html', {
                'items': [],
                'subtotal_carrito': 0,
                'descuento_cupon': 0,
                'total_carrito': 0,
                'cart_count': 0,
                'compra_exitosa': True,
                'ultima_compra': compra,
                'compras_usuario': compras_recientes,
                'cupones_disponibles': CUPONES_DISPONIBLES,
            })

        items = list(items_qs)
        compras_recientes = Compra.objects.filter(usuario=request.user).prefetch_related('detalles')[:5]
    else:
        if request.method == 'POST':
            login_url = f"{reverse('login')}?next={reverse('ver_carrito')}"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'redirect': login_url}, status=401)
            return redirect(login_url)

        carrito_invitado = request.session.get('carrito_invitado', {})
        items = []
        for pid_str, cant in carrito_invitado.items():
            try:
                prod = Producto.objects.get(id=int(pid_str))
                items.append(ItemInvitado(prod, int(cant)))
            except (Producto.DoesNotExist, ValueError):
                continue
        compras_recientes = []

    subtotal_carrito = sum(i.subtotal for i in items)
    cart_count = sum(i.cantidad for i in items)
    descuento_cupon, total_carrito, info_cupon = calcular_descuento_cupon(subtotal_carrito, cupon_session)

    return render(request, 'catalogo/carrito.html', {
        'items': items,
        'subtotal_carrito': subtotal_carrito,
        'descuento_cupon': descuento_cupon,
        'cupon_info': info_cupon,
        'cupon_feedback': cupon_feedback,
        'cupones_disponibles': CUPONES_DISPONIBLES,
        'total_carrito': total_carrito,
        'cart_count': cart_count,
        'compras_usuario': compras_recientes,
    })


@login_required
def historial_compras(request):
    """Sector dedicado al historial de compras del usuario cliente. Los administradores no tienen compras personales."""
    if request.user.is_superuser:
        return redirect('panel_admin')
    sincronizar_carrito_invitado(request)
    compras = Compra.objects.filter(usuario=request.user).prefetch_related('detalles')
    cart_count = obtener_cantidad_carrito(request)
    return render(request, 'catalogo/historial.html', {
        'compras': compras,
        'cart_count': cart_count,
    })


class RegistroUsuarioForm(UserCreationForm):
    email = forms.EmailField(
        label="Correo Gmail (para recuperación de contraseña)",
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'ejemplo@gmail.com',
            'autocomplete': 'email',
        }),
        help_text="Ingresa tu correo @gmail.com. Te enviaremos un código aquí si olvidas tu contraseña.",
        error_messages={
            'required': "Por favor ingresa un correo Gmail.",
            'invalid': "Ingresa una dirección de correo válida.",
        }
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')
        error_messages = {
            'username': {
                'required': "Por favor ingresa un nombre de usuario.",
                'unique': "Este nombre de usuario ya está registrado en Vice City. Por favor elige otro.",
                'invalid': "El nombre de usuario solo puede contener letras, números y los caracteres @/./+/-/_.",
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_messages['password_mismatch'] = "Las contraseñas no coinciden. Por favor asegúrate de escribir la misma contraseña en ambos campos."

        if 'username' in self.fields:
            self.fields['username'].label = "Nombre de Usuario"
            self.fields['username'].help_text = "Requerido. Máximo 150 caracteres. Solo letras, números y los caracteres @/./+/-/_."
            self.fields['username'].widget.attrs.update({
                'placeholder': 'Ej: TommyVercetti',
                'autocomplete': 'username',
            })

        if 'password1' in self.fields:
            self.fields['password1'].label = "Contraseña"
            self.fields['password1'].help_text = "Mínimo 8 caracteres. Debe combinar letras y no ser una clave demasiado común o solo números."
            self.fields['password1'].widget.attrs.update({
                'placeholder': 'Ingresa tu contraseña',
                'autocomplete': 'new-password',
            })

        if 'password2' in self.fields:
            self.fields['password2'].label = "Confirmar Contraseña"
            self.fields['password2'].help_text = "Ingresa la misma contraseña anterior para verificación."
            self.fields['password2'].widget.attrs.update({
                'placeholder': 'Repite tu contraseña',
                'autocomplete': 'new-password',
            })

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError("Debes ingresar un correo Gmail válido.")
        if not email.endswith('@gmail.com'):
            raise forms.ValidationError("Por favor ingresa un correo con dominio @gmail.com.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo Gmail ya está registrado en otra cuenta de Vice City.")
        return email

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden. Por favor asegúrate de escribir la misma contraseña en ambos campos.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].strip().lower()
        if commit:
            user.save()
        return user


def registrar_usuario(request):
    """Registro público de nuevos usuarios desde el menú de Iniciar Sesión con correo Gmail."""
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            nuevo_user = form.save()
            PerfilUsuario.objects.get_or_create(usuario=nuevo_user)
            tenia_carrito = bool(request.session.get('carrito_invitado'))
            auth_login(request, nuevo_user)
            sincronizar_carrito_invitado(request, user=nuevo_user)
            if next_url:
                return redirect(next_url)
            if tenia_carrito or request.session.pop('redirigir_a_carrito', False):
                return redirect('ver_carrito')
            return redirect('inicio')
    else:
        form = RegistroUsuarioForm()

    return render(request, 'catalogo/registrar_usuario.html', {
        'form': form,
        'next_url': next_url,
    })


def recuperar_password(request):
    """Simula el envío de un código de 6 dígitos al Gmail del usuario para restablecer su contraseña."""
    paso = request.session.get('reset_pwd_step', 'solicitar')
    mensaje_error = None
    mensaje_exito = None

    if request.GET.get('reiniciar') == '1':
        for k in ('reset_pwd_step', 'reset_pwd_user_id', 'reset_pwd_email', 'reset_pwd_code', 'reset_pwd_username'):
            request.session.pop(k, None)
        return redirect('recuperar_password')

    if request.method == 'POST':
        accion = request.POST.get('accion', 'enviar_codigo')

        if accion == 'enviar_codigo':
            email_input = (request.POST.get('email') or '').strip().lower()
            username_input = (request.POST.get('username') or '').strip()

            if not email_input or '@gmail.com' not in email_input:
                mensaje_error = "Por favor ingresa un correo @gmail.com válido."
                paso = 'solicitar'
            else:
                # Buscar primero por correo Gmail registrado
                usuario = User.objects.filter(email__iexact=email_input).first()
                # Si es una cuenta antigua que no tenía email guardado y puso su usuario, vincularlo
                if not usuario and username_input:
                    usuario = User.objects.filter(username__iexact=username_input).first()
                    if usuario and not usuario.email:
                        usuario.email = email_input
                        usuario.save()

                if not usuario:
                    mensaje_error = (
                        "No encontramos una cuenta con ese Gmail. "
                        "Si creaste tu cuenta antes sin Gmail, escribe también tu nombre de usuario abajo."
                    )
                    paso = 'solicitar'
                else:
                    codigo = f"{random.randint(100000, 999999)}"
                    request.session['reset_pwd_step'] = 'verificar'
                    request.session['reset_pwd_user_id'] = usuario.id
                    request.session['reset_pwd_email'] = email_input
                    request.session['reset_pwd_username'] = usuario.username
                    request.session['reset_pwd_code'] = codigo
                    request.session.modified = True
                    paso = 'verificar'

        elif accion == 'cambiar_password':
            codigo_ingresado = (request.POST.get('codigo') or '').strip()
            nueva_password = (request.POST.get('nueva_password') or '').strip()
            confirmar_password = (request.POST.get('confirmar_password') or '').strip()

            codigo_real = request.session.get('reset_pwd_code')
            user_id = request.session.get('reset_pwd_user_id')

            if not codigo_real or not user_id:
                mensaje_error = "La sesión de recuperación expiró. Solicita un nuevo código."
                paso = 'solicitar'
            elif codigo_ingresado != str(codigo_real):
                mensaje_error = "El código ingresado es incorrecto. Revisa el correo simulado de Gmail arriba."
                paso = 'verificar'
            elif len(nueva_password) < 4:
                mensaje_error = "La nueva contraseña debe tener al menos 4 caracteres."
                paso = 'verificar'
            elif nueva_password != confirmar_password:
                mensaje_error = "Las contraseñas no coinciden. Inténtalo de nuevo."
                paso = 'verificar'
            else:
                usuario = User.objects.filter(id=user_id).first()
                if not usuario:
                    mensaje_error = "Usuario no encontrado."
                    paso = 'solicitar'
                else:
                    usuario.set_password(nueva_password)
                    usuario.save()
                    for k in ('reset_pwd_step', 'reset_pwd_user_id', 'reset_pwd_email', 'reset_pwd_code', 'reset_pwd_username'):
                        request.session.pop(k, None)
                    return redirect(f"{reverse('login')}?reset=ok")

    context = {
        'paso': paso,
        'mensaje_error': mensaje_error,
        'mensaje_exito': mensaje_exito,
        'reset_email': request.session.get('reset_pwd_email', ''),
        'reset_username': request.session.get('reset_pwd_username', ''),
        'reset_code': request.session.get('reset_pwd_code', ''),
    }
    return render(request, 'catalogo/recuperar_password.html', context)


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'precio', 'stock', 'imagen', 'imagen_url']


@user_passes_test(lambda u: u.is_superuser)
def agregar_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('buscar_productos')
    else:
        form = ProductoForm()

    return render(request, 'catalogo/agregar_producto.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        producto.delete()
        return redirect('buscar_productos')

    return render(request, 'catalogo/eliminar_producto.html', {'producto': producto})


@user_passes_test(lambda u: u.is_superuser)
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('buscar_productos')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'catalogo/editar_producto.html', {'form': form, 'producto': producto})


@login_required
def ver_boleta(request, compra_id):
    """Muestra la Boleta Electrónica imprimible de una compra (dueño de la compra o Admin)."""
    if not request.user.is_authenticated:
        messages.info(request, "Inicia sesión para visualizar tu boleta electrónica.")
        return redirect('login')

    try:
        if request.user.is_superuser:
            compra = Compra.objects.prefetch_related('detalles').get(id=compra_id)
        else:
            compra = Compra.objects.prefetch_related('detalles').get(id=compra_id, usuario=request.user)
    except Compra.DoesNotExist:
        messages.warning(request, f'La boleta #{compra_id:04d} no existe o fue reiniciada a 0. Las nuevas compras comenzarán desde la #0001.')
        if request.user.is_superuser:
            return redirect('panel_admin')
        return redirect('historial_compras')

    cart_count = obtener_cantidad_carrito(request)
    return render(request, 'catalogo/boleta.html', {
        'compra': compra,
        'cart_count': cart_count,
    })


def detalle_producto(request, producto_id):
    """Página de detalle completo del producto con reseñas 1-5 estrellas, productos similares y favoritos."""
    if request.user.is_authenticated:
        sincronizar_carrito_invitado(request)

    producto = get_object_or_404(Producto, id=producto_id)

    # Funcionalidad de sesiones (ES3 - Criterio 2.1.4): Registro de los últimos 3 productos visitados
    ultimos = request.session.get('ultimos_visitados', [])
    if producto.id in ultimos:
        ultimos.remove(producto.id)
    ultimos.insert(0, producto.id)
    request.session['ultimos_visitados'] = ultimos[:3]
    request.session.modified = True

    mensaje_resena = None
    error_resena = None

    if request.method == 'POST' and request.POST.get('accion') == 'publicar_resena':
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={reverse('detalle_producto', args=[producto.id])}")

        comentario = (request.POST.get('comentario') or '').strip()
        try:
            estrellas = max(1, min(5, int(request.POST.get('estrellas', 5))))
        except ValueError:
            estrellas = 5

        if len(comentario) < 3:
            error_resena = "Escribe un comentario de al menos 3 caracteres para compartir tu opinión."
        else:
            ResenaProducto.objects.create(
                producto=producto,
                usuario=request.user,
                estrellas=estrellas,
                comentario=comentario,
            )
            mensaje_resena = "¡Gracias! Tu valoración fue publicada en la ficha del producto."

    resenas = list(producto.resenas.select_related('usuario', 'usuario__perfil').all())
    total_resenas = len(resenas)
    if total_resenas > 0:
        promedio_estrellas = round(sum(r.estrellas for r in resenas) / total_resenas, 1)
    else:
        promedio_estrellas = 5.0

    unidades_vendidas = (
        DetalleCompra.objects.filter(producto=producto).aggregate(total=Sum('cantidad'))['total'] or 0
    )

    relacionados = list(
        Producto.objects.filter(categoria__iexact=producto.categoria)
        .exclude(id=producto.id)[:4]
    )
    if len(relacionados) < 4:
        extras = list(
            Producto.objects.exclude(id__in=[producto.id] + [p.id for p in relacionados])[:(4 - len(relacionados))]
        )
        relacionados.extend(extras)

    favoritos_ids = obtener_ids_favoritos(request)
    es_favorito = producto.id in favoritos_ids
    cart_count = obtener_cantidad_carrito(request)

    return render(request, 'catalogo/detalle_producto.html', {
        'producto': producto,
        'cuota_6': max(1, producto.precio // 6),
        'resenas': resenas,
        'total_resenas': total_resenas,
        'promedio_estrellas': promedio_estrellas,
        'unidades_vendidas': unidades_vendidas,
        'relacionados': relacionados,
        'es_favorito': es_favorito,
        'favoritos_ids': favoritos_ids,
        'fav_count': len(favoritos_ids),
        'cart_count': cart_count,
        'mensaje_resena': mensaje_resena,
        'error_resena': error_resena,
    })


def toggle_favorito(request, producto_id):
    """Agrega o quita un producto de Favoritos (soporta tanto usuarios autenticados como invitados y AJAX)."""
    if request.user.is_authenticated and request.user.is_superuser:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'El administrador no gestiona favoritos.', 'fav_count': 0})
        messages.info(request, "Los administradores no gestionan favoritos personales.")
        return redirect('panel_admin')

    producto = get_object_or_404(Producto, id=producto_id)
    es_favorito = False

    if request.user.is_authenticated:
        fav_obj, creado = Favorito.objects.get_or_create(usuario=request.user, producto=producto)
        if not creado:
            fav_obj.delete()
            es_favorito = False
        else:
            es_favorito = True
        fav_count = Favorito.objects.filter(usuario=request.user).count()
    else:
        favs = [int(x) for x in request.session.get('favoritos_invitado', []) if str(x).isdigit()]
        if producto.id in favs:
            favs.remove(producto.id)
            es_favorito = False
        else:
            favs.append(producto.id)
            es_favorito = True
        request.session['favoritos_invitado'] = favs
        request.session.modified = True
        fav_count = len(favs)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'producto_id': producto.id,
            'es_favorito': es_favorito,
            'fav_count': fav_count,
            'producto_nombre': producto.nombre,
        })

    next_url = request.POST.get('next') or request.GET.get('next') or request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('mis_favoritos')


def mis_favoritos(request):
    """Muestra la lista de productos guardados en Favoritos ❤️."""
    if request.user.is_authenticated and request.user.is_superuser:
        messages.info(request, "Los administradores no gestionan favoritos personales.")
        return redirect('panel_admin')

    if request.user.is_authenticated:
        sincronizar_carrito_invitado(request)
    favoritos_ids = obtener_ids_favoritos(request)
    productos_favoritos = list(Producto.objects.filter(id__in=favoritos_ids))
    cart_count = obtener_cantidad_carrito(request)

    return render(request, 'catalogo/favoritos.html', {
        'productos': productos_favoritos,
        'favoritos_ids': favoritos_ids,
        'fav_count': len(productos_favoritos),
        'cart_count': cart_count,
    })


def api_autocompletar(request):
    """Endpoint JSON para autocompletado instantáneo en la barra de búsqueda."""
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'resultados': []})

    q_norm = _normalizar_texto(q)
    coincidencias = []
    for p in Producto.objects.all():
        if q_norm in _normalizar_texto(p.nombre) or q_norm in _normalizar_texto(p.categoria):
            img = ''
            if p.imagen:
                try:
                    img = p.imagen.url
                except ValueError:
                    img = ''
            elif p.imagen_url:
                img = p.imagen_url

            coincidencias.append({
                'id': p.id,
                'nombre': p.nombre,
                'categoria': p.categoria,
                'precio': p.precio,
                'stock': p.stock,
                'imagen': img,
                'url': reverse('detalle_producto', args=[p.id]),
            })
            if len(coincidencias) >= 6:
                break

    return JsonResponse({'resultados': coincidencias})


@user_passes_test(lambda u: u.is_superuser)
def panel_admin(request):
    """Dashboard Ejecutivo para el Admin con métricas de ventas, stock crítico y reposición rápida."""
    compras = Compra.objects.select_related('usuario').prefetch_related('detalles').all()
    total_ingresos = sum(c.total for c in compras)
    total_pedidos = compras.count()
    ticket_promedio = int(round(total_ingresos / total_pedidos)) if total_pedidos > 0 else 0
    total_clientes = User.objects.count()

    productos = list(Producto.objects.all().order_by('stock', 'nombre'))
    productos_stock_bajo = [p for p in productos if p.stock <= 5]
    productos_agotados = [p for p in productos if p.stock == 0]

    # Top productos más vendidos
    ventas_agrupadas = (
        DetalleCompra.objects.values('nombre_producto', 'categoria_producto')
        .annotate(unidades=Sum('cantidad'), recaudado=Sum('precio_unitario'))
        .order_by('-unidades')[:6]
    )

    cart_count = obtener_cantidad_carrito(request)
    mensaje_stock = request.session.pop('admin_stock_msg', None)

    return render(request, 'catalogo/panel_admin.html', {
        'total_ingresos': total_ingresos,
        'total_pedidos': total_pedidos,
        'ticket_promedio': ticket_promedio,
        'total_clientes': total_clientes,
        'total_productos': len(productos),
        'productos_stock_bajo': productos_stock_bajo,
        'productos_agotados_count': len(productos_agotados),
        'ventas_agrupadas': ventas_agrupadas,
        'compras_recientes': compras[:10],
        'cart_count': cart_count,
        'mensaje_stock': mensaje_stock,
    })


@user_passes_test(lambda u: u.is_superuser)
def gestion_despachos(request):
    """Página dedicada e independiente para que el Administrador gestione todos los pedidos y despachos."""
    compras_qs = Compra.objects.select_related('usuario').prefetch_related('detalles').all()

    # Búsqueda por folio (#0001, 1) o usuario
    q = (request.GET.get('q') or '').strip()
    if q:
        if q.startswith('#'):
            num_clean = q.replace('#', '').lstrip('0')
            if num_clean.isdigit():
                compras_qs = compras_qs.filter(id=int(num_clean))
            else:
                compras_qs = compras_qs.filter(usuario__username__icontains=q)
        elif q.isdigit():
            compras_qs = compras_qs.filter(id=int(q))
        else:
            compras_qs = compras_qs.filter(usuario__username__icontains=q)

    # Filtro por tipo o estado
    filtro_estado = (request.GET.get('filtro') or 'todos').strip().lower()
    if filtro_estado == 'pendientes':
        compras_qs = compras_qs.filter(estado_envio__in=['aprobado', 'bodega'])
    elif filtro_estado == 'en_ruta':
        compras_qs = compras_qs.filter(estado_envio='en_ruta')
    elif filtro_estado == 'listo_retiro':
        compras_qs = compras_qs.filter(estado_envio='listo_retiro')
    elif filtro_estado == 'retiros':
        compras_qs = compras_qs.filter(metodo_pago__icontains='retiro')
    elif filtro_estado == 'entregados':
        compras_qs = compras_qs.filter(estado_envio='entregado')

    todas = Compra.objects.all()
    cart_count = obtener_cantidad_carrito(request)

    return render(request, 'catalogo/despachos_admin.html', {
        'compras': compras_qs,
        'q': q,
        'filtro_actual': filtro_estado,
        'total_pedidos': todas.count(),
        'total_pendientes': todas.filter(estado_envio__in=['aprobado', 'bodega']).count(),
        'total_en_ruta': todas.filter(estado_envio='en_ruta').count(),
        'total_listo_retiro': todas.filter(estado_envio='listo_retiro').count(),
        'total_retiros': todas.filter(metodo_pago__icontains='retiro').count(),
        'total_entregados': todas.filter(estado_envio='entregado').count(),
        'cart_count': cart_count,
    })


@user_passes_test(lambda u: u.is_superuser)
def reponer_stock(request, producto_id):
    """Permite al Admin sumar stock rápidamente desde el Dashboard."""
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        try:
            cantidad_sumar = max(1, int(request.POST.get('cantidad', 10)))
        except ValueError:
            cantidad_sumar = 10
        producto.stock += cantidad_sumar
        producto.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': True,
                'producto_id': producto.id,
                'nuevo_stock': producto.stock,
                'mensaje': f"Stock de {producto.nombre} actualizado a {producto.stock} unidades.",
            })
        request.session['admin_stock_msg'] = f"¡Se agregaron +{cantidad_sumar} unidades a '{producto.nombre}' (Stock actual: {producto.stock})!"
    return redirect('panel_admin')


@user_passes_test(lambda u: u.is_superuser)
def actualizar_estado_compra(request, compra_id):
    """Permite al Admin cambiar el estado de despacho de una compra sin recargar la página."""
    compra = get_object_or_404(Compra, id=compra_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado_envio', '').strip()
        if not nuevo_estado and request.body:
            import json
            try:
                data = json.loads(request.body.decode('utf-8'))
                nuevo_estado = (data.get('estado_envio') or '').strip()
            except Exception:
                pass

        estados_validos = [choice[0] for choice in Compra.ESTADO_CHOICES]
        if nuevo_estado in estados_validos:
            compra.estado_envio = nuevo_estado
            compra.save()
            msg = f"Estado de boleta #000{compra.id} actualizado a '{compra.estado_display}'."
            messages.success(request, msg)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True,
                    'compra_id': compra.id,
                    'nuevo_estado': compra.estado_envio,
                    'estado_display': compra.estado_display,
                    'step': compra.estado_step,
                    'mensaje': msg,
                })
        else:
            messages.error(request, "Estado de despacho no válido.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': 'Estado no válido'}, status=400)

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('panel_admin')
    return redirect(next_url)


# ==============================================================================
# EVALUACIÓN SUMATIVA 3 (ES3) - REPORTES CON ORM & FORMULARIO DE CLIENTES
# ==============================================================================

def reporte_categorias(request):
    """
    Reporte 1 (ES3 - Criterio 2.1.3 / Indicador 4 & 6):
    Resumen por agrupación utilizando annotate() y aggregate() del ORM de Django.
    Calcula por categoría: cantidad de registros, total de stock y precio promedio.
    Todos los cálculos están resueltos en la vista mediante el ORM, no en el template.
    """
    # 1. Agrupación y cálculos por categoría con annotate()
    datos_categorias = (
        Producto.objects.values('categoria')
        .annotate(
            total_productos=Count('id'),
            stock_total=Sum('stock'),
            precio_promedio=Avg('precio'),
            precio_minimo=Min('precio'),
            precio_maximo=Max('precio'),
        )
        .order_by('categoria')
    )

    # 2. Métricas globales consolidadas con aggregate()
    totales_globales = Producto.objects.aggregate(
        gran_total_productos=Count('id'),
        gran_total_stock=Sum('stock'),
        precio_promedio_general=Avg('precio'),
        precio_max_absoluto=Max('precio'),
        precio_min_absoluto=Min('precio'),
    )

    # Total de categorías distintas
    total_categorias = len(datos_categorias)

    return render(request, 'catalogo/reporte_categorias.html', {
        'datos_categorias': datos_categorias,
        'totales_globales': totales_globales,
        'total_categorias': total_categorias,
    })


def reporte_stock_critico(request):
    """
    Reporte 2 (ES3 - Criterio 2.1.3 / Indicador 5 & 6):
    Listado filtrado con el ORM de Django: registros bajo un umbral de stock crítico.
    Utiliza filter() y order_by() en el ORM.
    Cálculos resueltos en la vista con el ORM, no en el template.
    """
    # Umbral de stock crítico parametrizable (por defecto 5 unidades)
    umbral_str = request.GET.get('umbral', '5').strip()
    try:
        umbral = max(1, int(umbral_str))
    except ValueError:
        umbral = 5

    # Consulta ORM: filtrado y ordenamiento
    productos_criticos = (
        Producto.objects.filter(stock__lte=umbral)
        .order_by('stock', 'precio')
    )

    # Agregación sobre el conjunto filtrado con aggregate()
    resumen_critico = productos_criticos.aggregate(
        total_criticos=Count('id'),
        stock_total_critico=Sum('stock'),
        precio_promedio_critico=Avg('precio'),
    )

    return render(request, 'catalogo/reporte_stock_critico.html', {
        'productos_criticos': productos_criticos,
        'umbral': umbral,
        'resumen_critico': resumen_critico,
        'total_criticos': resumen_critico['total_criticos'] or 0,
    })


def contacto_cliente(request):
    """
    Formulario de Contacto y Consultas de Clientes (ES3 - Criterio 2.1.4 / Indicador 7 & 8).
    Utiliza ModelForm con validaciones operativas (campos obligatorios, formato de correo,
    largos mínimos); la vista guarda en la BD (modelo ConsultaCliente) y entrega confirmación.
    """
    if request.user.is_authenticated:
        sincronizar_carrito_invitado(request)

    producto_id = request.GET.get('producto')
    consulta_exitosa = False
    datos_consulta = None

    if request.method == 'POST':
        form = ConsultaClienteForm(request.POST)
        if form.is_valid():
            nueva_consulta = form.save()
            consulta_exitosa = True
            datos_consulta = nueva_consulta
            messages.success(
                request,
                f"¡Gracias, {nueva_consulta.nombre}! Tu consulta ha sido registrada exitosamente en nuestra base de datos. Nos comunicaremos contigo a {nueva_consulta.correo}."
            )
            form = ConsultaClienteForm()  # Formulario limpio
        else:
            messages.error(
                request,
                "Por favor corrige los campos marcados en rojo. Asegúrate de ingresar un correo válido y detallar tu consulta."
            )
    else:
        initial_data = {}
        if producto_id and producto_id.isdigit():
            initial_data['producto_interes'] = int(producto_id)
        if request.user.is_authenticated:
            initial_data['nombre'] = request.user.get_full_name() or request.user.username
            if request.user.email:
                initial_data['correo'] = request.user.email
        form = ConsultaClienteForm(initial=initial_data)

    return render(request, 'catalogo/contacto.html', {
        'form': form,
        'consulta_exitosa': consulta_exitosa,
        'datos_consulta': datos_consulta,
    })

