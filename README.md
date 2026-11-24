# 🛠️ Ferretería VI — Catálogo Online & API RESTful con JWT
**Asignatura:** Programación Back End (TI3041) · INACAP  
**Evaluación:** Evaluación Sumativa 4 (ES4) — Unidad 3: API RESTful con integración a base de datos y autenticación JWT  
**Estudiante:** Jordan Loaiza  
**Sección / Negocio:** Variante A — Ferretería (`nombre`, `categoria`, `precio`, `stock` · +40 productos)

---

## 📋 Descripción del Proyecto

Plataforma web y **API RESTful** para la gestión del catálogo de **Ferretería VI**, desarrollada con **Django**, **Django REST Framework (DRF)** y **SimpleJWT**.

* **Catálogo Web & CRUD:** Gestión completa de productos desde la interfaz web, carrito de compras, boleta electrónica, reportes con ORM (`annotate`, `aggregate`, `filter`, `order_by`), formulario de contacto de clientes (`ModelForm`) y manejo de sesiones.
* **API RESTful (`/api/productos/`):**
  * **Lectura pública (`GET`):** Listado completo y detalle por ID en formato JSON (`200 OK`, `404 Not Found`).
  * **Escritura protegida con JWT (`POST`, `PUT`, `PATCH`, `DELETE`):** Requiere token `Bearer` válido (`401 Unauthorized` sin token, `400 Bad Request` ante datos inválidos, `201 Created`, `200 OK`, `204 No Content`).
* **Base de Datos Poblamiento Automático:** El archivo `db.sqlite3` está excluido del repositorio (`.gitignore`). Al ejecutar `python manage.py migrate`, el sistema carga automáticamente los **41 productos con imágenes** desde [`productos.json`](./productos.json) y crea el superusuario de pruebas.

---

## 🚀 Instalación y Puesta en Marcha (Paso a Paso)

### 1. Clonar el repositorio
```bash
git clone https://github.com/jordanloaiza87-coder/loaiza-ti3041-es4.git
cd loaiza-ti3041-es4
```

### 2. Crear y activar entorno virtual (opcional pero recomendado)
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Instalar dependencias
```powershell
pip install -r requirements.txt
```

### 4. Migrar y poblar la base de datos
```powershell
python manage.py migrate
python manage.py loaddata productos.json
```
*(Nota: Al ejecutar `migrate`, una señal `post_migrate` en `catalogo/apps.py` también carga automáticamente `productos.json` y crea el superusuario `jordanAdmin` si la base de datos está vacía).*

### 5. Ejecutar el servidor de desarrollo
```powershell
python manage.py runserver
```
* **Sitio Web:** `http://localhost:8000/`
* **API REST Productos:** `http://localhost:8000/api/productos/`
* **Panel Admin Django:** `http://localhost:8000/admin/`

---

## 🔑 Credenciales de Superusuario para Pruebas JWT y Admin

* **Usuario:** `jordanAdmin` *(o `admin`)*
* **Contraseña:** `admin1234`

---

## 🌐 Endpoints de la API REST y Autenticación JWT

| Método | Endpoint | Permiso | Descripción | Códigos de Respuesta |
|---|---|---|---|---|
| `GET` | `/api/productos/` | Público | Lista todos los productos del catálogo en JSON | `200 OK` |
| `GET` | `/api/productos/<id>/` | Público | Obtiene el detalle de un producto específico | `200 OK` · `404 Not Found` |
| `POST` | `/api/token/` | Público | Obtiene el par de tokens JWT (`access` y `refresh`) | `200 OK` · `401 Unauthorized` |
| `POST` | `/api/token/refresh/` | Público | Refresca el token de acceso (`access`) usando `refresh` | `200 OK` · `401 Unauthorized` |
| `POST` | `/api/productos/` | **JWT Bearer** | Crea un nuevo producto validando campos | `201 Created` · `400 Bad Request` · `401 Unauthorized` |
| `PUT` | `/api/productos/<id>/` | **JWT Bearer** | Actualiza todos los campos de un producto | `200 OK` · `400 Bad Request` · `401 Unauthorized` · `404 Not Found` |
| `PATCH` | `/api/productos/<id>/` | **JWT Bearer** | Actualiza parcialmente un producto (ej. `stock`) | `200 OK` · `400 Bad Request` · `401 Unauthorized` · `404 Not Found` |
| `DELETE` | `/api/productos/<id>/` | **JWT Bearer** | Elimina un producto de la base de datos | `204 No Content` · `401 Unauthorized` · `404 Not Found` |

---

## 🧪 Pruebas Automatizadas y Colección de la API

1. **Colección Postman / Thunder Client:** [`coleccion_pruebas_api.json`](./coleccion_pruebas_api.json)
2. **Reporte de Ejecución Real (`curl` + Esperado vs Obtenido):** [`pruebas_api.md`](./pruebas_api.md)
3. **Documento de Trazabilidad y Uso de IA:** [`uso_ia.md`](./uso_ia.md)
4. **Ejecutar tests automatizados de Django REST Framework:**
   ```powershell
   python manage.py test
   ```

---

## 📦 Estructura de Commits de la Evaluación (ES4)

1. `etapa-0-drf`: Configuración de entorno, `djangorestframework`, `djangorestframework-simplejwt` y `productos.json`.
2. `etapa-1-lectura`: `ProductoSerializer` con validaciones y endpoints `GET` de listado y detalle.
3. `etapa-2-escritura`: Endpoints `POST`, `PUT`, `PATCH` y `DELETE` con validación `400 Bad Request`.
4. `etapa-3-jwt`: Configuración de `/api/token/`, `/api/token/refresh/`, seguridad JWT y protección `401 Unauthorized`.
5. `entrega-final`: Colección de pruebas ejecutada, [`pruebas_api.md`](./pruebas_api.md), [`uso_ia.md`](./uso_ia.md) y [`README.md`](./README.md).
