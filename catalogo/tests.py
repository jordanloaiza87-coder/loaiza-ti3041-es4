from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Producto


class ProductoAPITestCase(APITestCase):
    """
    Pruebas automatizadas de la API REST del catálogo con autenticación JWT (ES4).
    Verifica lectura pública (200, 404), protección JWT (401 sin token) y escritura autenticada (201, 400, 200, 204).
    """

    def setUp(self):
        self.admin_user = User.objects.filter(username='jordanAdmin').first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('jordanAdmin', 'jordan@ferreteriavi.cl', 'admin1234')
        else:
            self.admin_user.set_password('admin1234')
            self.admin_user.save()

        self.producto = Producto.objects.first()
        if not self.producto:
            self.producto = Producto.objects.create(
                nombre="Martillo Carpintero",
                categoria="Herramientas",
                precio=6500,
                stock=8,
            )

    def obtener_token_jwt(self):
        resp = self.client.post('/api/token/', {
            'username': 'jordanAdmin',
            'password': 'admin1234',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)
        return resp.data['access'], resp.data['refresh']

    def test_1_listado_publico_productos(self):
        resp = self.client.get('/api/productos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_2_detalle_existente_e_inexistente(self):
        resp_ok = self.client.get(f'/api/productos/{self.producto.id}/')
        self.assertEqual(resp_ok.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_ok.data['nombre'], self.producto.nombre)

        resp_404 = self.client.get('/api/productos/99999/')
        self.assertEqual(resp_404.status_code, status.HTTP_404_NOT_FOUND)

    def test_3_escritura_sin_token_retorna_401(self):
        resp = self.client.post('/api/productos/', {
            'nombre': 'Producto Sin Token',
            'categoria': 'Herramientas',
            'precio': 10000,
            'stock': 5,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_4_creacion_valida_e_invalida_con_jwt(self):
        access, _ = self.obtener_token_jwt()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        # POST válido -> 201 Created
        resp_ok = self.client.post('/api/productos/', {
            'nombre': 'Taladro Inalámbrico 20V',
            'categoria': 'Eléctricas',
            'precio': 54990,
            'stock': 15,
        }, format='json')
        self.assertEqual(resp_ok.status_code, status.HTTP_201_CREATED)

        # POST inválido (precio negativo, nombre vacío) -> 400 Bad Request
        resp_bad = self.client.post('/api/productos/', {
            'nombre': '',
            'categoria': 'Eléctricas',
            'precio': -500,
            'stock': -2,
        }, format='json')
        self.assertEqual(resp_bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_5_actualizacion_y_eliminacion_con_jwt(self):
        access, _ = self.obtener_token_jwt()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        # PUT -> 200 OK
        resp_put = self.client.put(f'/api/productos/{self.producto.id}/', {
            'nombre': 'Martillo Carpintero Pro',
            'categoria': 'Herramientas',
            'precio': 7990,
            'stock': 20,
        }, format='json')
        self.assertEqual(resp_put.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_put.data['precio'], 7990)

        # DELETE -> 204 No Content
        resp_del = self.client.delete(f'/api/productos/{self.producto.id}/')
        self.assertEqual(resp_del.status_code, status.HTTP_204_NO_CONTENT)
