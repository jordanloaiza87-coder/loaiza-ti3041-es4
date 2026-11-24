# Documentación y Resultados de Pruebas de la API REST (`pruebas_api.md`)
**Asignatura:** Programación Back End (TI3041)  
**Evaluación:** Evaluación Sumativa 4 (ES4) — API RESTful con Autenticación JWT  
**Estudiante:** Jordan Loaiza  
**Proyecto:** Catálogo Online — Ferretería VI  

---

## 1. Credenciales y Configuración Base de Pruebas
* **URL Base:** `http://localhost:8000`
* **Endpoint de Productos:** `http://localhost:8000/api/productos/`
* **Endpoint de Token JWT:** `http://localhost:8000/api/token/`
* **Endpoint de Refresco JWT:** `http://localhost:8000/api/token/refresh/`
* **Superusuario de prueba (creado automáticamente al migrar):**
  * **Usuario:** `jordanAdmin` (o `admin`)
  * **Contraseña:** `admin1234`
* **Archivo de colección importable (Postman / Thunder Client):** [`coleccion_pruebas_api.json`](./coleccion_pruebas_api.json)

---

## 2. Resumen de Ejecución Real (Esperado vs Obtenido)

Durante la primera ejecución de la batería de pruebas se detectaron dos discrepancias que fueron corregidas antes de la validación definitiva:
1. **En la Prueba 4 (`POST /api/productos/` sin token):** Inicialmente, al tener `SessionAuthentication` habilitado junto con `JWTAuthentication` en las opciones por defecto de DRF, la API respondía con **`403 Forbidden`** en vez de **`401 Unauthorized`**. **Corrección:** Se configuró explícitamente `authentication_classes = [JWTAuthentication]` en las vistas de la API y en `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`, logrando que devuelva **`401 Unauthorized`** con el encabezado `WWW-Authenticate: Bearer realm="api"`.
2. **En la Prueba 8 (`POST /api/productos/` con precio negativo):** Inicialmente el `ModelSerializer` por defecto de Django permitía enteros negativos en `IntegerField` (`precio: -500`), devolviendo **`201 Created`** en vez de **`400 Bad Request`**. **Corrección:** Se implementaron los métodos `validate_precio` (`precio > 0`) y `validate_stock` (`stock >= 0`) en `ProductoSerializer` (`catalogo/serializers.py`), rechazando correctamente los datos inválidos con **`400 Bad Request`**.

| N° | Caso de Prueba | Método y Endpoint | Autenticación | Código Esperado | Obtenido (1ª Ejecución) | Obtenido (Final) | Estado |
|---|---|---|---|---|---|---|---|
| **1** | Listado completo del catálogo | `GET /api/productos/` | Pública (Sin token) | `200 OK` | `200 OK` | `200 OK` | ✅ Aprobado |
| **2** | Detalle de producto existente | `GET /api/productos/1/` | Pública (Sin token) | `200 OK` | `200 OK` | `200 OK` | ✅ Aprobado |
| **3** | Detalle de producto inexistente | `GET /api/productos/9999/` | Pública (Sin token) | `404 Not Found` | `404 Not Found` | `404 Not Found` | ✅ Aprobado |
| **4** | Intento de escritura sin token JWT | `POST /api/productos/` | Sin token | `401 Unauthorized` | `403 Forbidden` *(Corregido)* | `401 Unauthorized` | ✅ Corregido y Aprobado |
| **5** | Obtención de par de tokens JWT | `POST /api/token/` | Credenciales Superuser | `200 OK` | `200 OK` | `200 OK` | ✅ Aprobado |
| **6** | Refresco de token de acceso JWT | `POST /api/token/refresh/` | Refresh Token | `200 OK` | `200 OK` | `200 OK` | ✅ Aprobado |
| **7** | Creación válida de producto | `POST /api/productos/` | `Bearer <access_token>` | `201 Created` | `201 Created` | `201 Created` | ✅ Aprobado |
| **8** | Creación inválida (precio/stock negativos y nombre vacío) | `POST /api/productos/` | `Bearer <access_token>` | `400 Bad Request` | `201 Created` *(Corregido)* | `400 Bad Request` | ✅ Corregido y Aprobado |
| **9** | Actualización completa (`PUT`) | `PUT /api/productos/42/` | `Bearer <access_token>` | `200 OK` | `200 OK` | `200 OK` | ✅ Aprobado |
| **10** | Actualización parcial (`PATCH`) | `PATCH /api/productos/42/` | `Bearer <access_token>` | `200 OK` | `200 OK` | `200 OK` | ✅ Aprobado |
| **11** | Eliminación de producto (`DELETE`) | `DELETE /api/productos/42/` | `Bearer <access_token>` | `204 No Content` | `204 No Content` | `204 No Content` | ✅ Aprobado |

---

## 3. Detalle de Comandos `curl` Ejecutados y Respuestas JSON Reales

### Prueba 1: Listado completo de productos (`GET /api/productos/`) — Público
**Comando:**
```bash
curl -i -X GET http://localhost:8000/api/productos/
```
**Resultado obtenido (`200 OK` - 41 productos en BD):**
```json
[
  {
    "id": 1,
    "nombre": "Martillo Carpintero",
    "categoria": "Herramientas",
    "precio": 6500,
    "stock": 8,
    "imagen": null,
    "imagen_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSH-lvrZx7Hn1qjz4s-8bA8p1IDtZHfe-SFhcNVtplRKA&s=10"
  },
  {
    "id": 2,
    "nombre": "Destornillador Cruz",
    "categoria": "Herramientas",
    "precio": 2500,
    "stock": 24,
    "imagen": null,
    "imagen_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSthAdYoBzGE96Yyav6DtsZ8CDb6W9f92HGxYzYtCCUIQ&s=10"
  }
]
```

---

### Prueba 2: Detalle de producto existente (`GET /api/productos/1/`) — Público
**Comando:**
```bash
curl -i -X GET http://localhost:8000/api/productos/1/
```
**Resultado obtenido (`200 OK`):**
```json
{
  "id": 1,
  "nombre": "Martillo Carpintero",
  "categoria": "Herramientas",
  "precio": 6500,
  "stock": 8,
  "imagen": null,
  "imagen_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSH-lvrZx7Hn1qjz4s-8bA8p1IDtZHfe-SFhcNVtplRKA&s=10"
}
```

---

### Prueba 3: Detalle de producto inexistente (`GET /api/productos/9999/`) — Público
**Comando:**
```bash
curl -i -X GET http://localhost:8000/api/productos/9999/
```
**Resultado obtenido (`404 Not Found`):**
```json
{
  "detail": "No Producto matches the given query."
}
```

---

### Prueba 4: Escritura SIN token JWT (`POST /api/productos/`) — Protegido
**Comando:**
```bash
curl -i -X POST http://localhost:8000/api/productos/ \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Sierra Test", "categoria": "Herramientas", "precio": 15000, "stock": 10}'
```
**Resultado obtenido (`401 Unauthorized`):**
```json
{
  "detail": "Las credenciales de autenticación no se proveyeron."
}
```

---

### Prueba 5: Obtención de Token JWT con Superusuario (`POST /api/token/`)
**Comando:**
```bash
curl -i -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "jordanAdmin", "password": "admin1234"}'
```
**Resultado obtenido (`200 OK`):**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### Prueba 6: Refresco de Token JWT (`POST /api/token/refresh/`)
**Comando:**
```bash
curl -i -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<REFRESH_TOKEN>"}'
```
**Resultado obtenido (`200 OK`):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### Prueba 7: Creación válida con Token JWT (`POST /api/productos/`)
**Comando:**
```bash
curl -i -X POST http://localhost:8000/api/productos/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"nombre": "Taladro Inalambrico 20V", "categoria": "Eléctricas", "precio": 54990, "stock": 15}'
```
**Resultado obtenido (`201 Created`):**
```json
{
  "id": 42,
  "nombre": "Taladro Inalambrico 20V",
  "categoria": "Eléctricas",
  "precio": 54990,
  "stock": 15,
  "imagen": null,
  "imagen_url": null
}
```

---

### Prueba 8: Creación inválida con Token JWT (`POST /api/productos/`)
**Comando:**
```bash
curl -i -X POST http://localhost:8000/api/productos/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"nombre": "", "categoria": "Eléctricas", "precio": -500, "stock": -2}'
```
**Resultado obtenido (`400 Bad Request`):**
```json
{
  "nombre": [
    "Este campo no puede estar en blanco."
  ],
  "precio": [
    "El precio debe ser un valor entero positivo mayor que 0."
  ],
  "stock": [
    "El stock disponible no puede ser un número negativo."
  ]
}
```

---

### Prueba 9: Actualización completa con Token JWT (`PUT /api/productos/42/`)
**Comando:**
```bash
curl -i -X PUT http://localhost:8000/api/productos/42/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"nombre": "Taladro Inalambrico 20V Pro", "categoria": "Eléctricas", "precio": 59990, "stock": 20}'
```
**Resultado obtenido (`200 OK`):**
```json
{
  "id": 42,
  "nombre": "Taladro Inalambrico 20V Pro",
  "categoria": "Eléctricas",
  "precio": 59990,
  "stock": 20,
  "imagen": null,
  "imagen_url": null
}
```

---

### Prueba 10: Actualización parcial con Token JWT (`PATCH /api/productos/42/`)
**Comando:**
```bash
curl -i -X PATCH http://localhost:8000/api/productos/42/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"stock": 35}'
```
**Resultado obtenido (`200 OK`):**
```json
{
  "id": 42,
  "nombre": "Taladro Inalambrico 20V Pro",
  "categoria": "Eléctricas",
  "precio": 59990,
  "stock": 35,
  "imagen": null,
  "imagen_url": null
}
```

---

### Prueba 11: Eliminación con Token JWT (`DELETE /api/productos/42/`)
**Comando:**
```bash
curl -i -X DELETE http://localhost:8000/api/productos/42/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
**Resultado obtenido (`204 No Content`):**
*(Sin cuerpo de respuesta, producto eliminado exitosamente de la base de datos).*
