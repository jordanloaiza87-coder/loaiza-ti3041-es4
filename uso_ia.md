# Registro de Uso de Inteligencia Artificial (`uso_ia.md`)
**Asignatura:** Programación Back End (TI3041)  
**Evaluación:** Evaluación Sumativa 4 (ES4) — API RESTful del Catálogo con Autenticación JWT  
**Estudiante:** Jordan Loaiza  
**Proyecto:** Catálogo Online — Ferretería VI  

---

## Parte 1: Registro de Consultas a la IA

### Consulta 1: Instalación y configuración de Django REST Framework y SimpleJWT
* **Prompt textual:**
  > *"Necesito configurar djangorestframework y djangorestframework-simplejwt en mi proyecto Django de Ferretería. Indícame cómo configurar INSTALLED_APPS y REST_FRAMEWORK en settings.py siguiendo la documentación oficial para que la lectura sea pública y la escritura requiera autenticación JWT."*
* **Resumen de la respuesta de la IA:**
  La IA indicó agregar `'rest_framework'` y `'rest_framework_simplejwt'` en `INSTALLED_APPS`, y definir el diccionario `REST_FRAMEWORK` configurando `DEFAULT_AUTHENTICATION_CLASSES` con `JWTAuthentication` y `DEFAULT_PERMISSION_CLASSES` con `IsAuthenticatedOrReadOnly`.
* **Qué se usó o modificó antes de integrarla:**
  Se verificó contra la documentación oficial de DRF y SimpleJWT, se instalaron los paquetes en el entorno virtual, se actualizó `requirements.txt` y se eliminó `SessionAuthentication` de las clases de autenticación de la API para evitar que las peticiones sin token devolvieran `403 Forbidden` en lugar del código estándar REST `401 Unauthorized`.

---

### Consulta 2: Serializer con validaciones y Endpoints CRUD REST (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`)
* **Prompt textual:**
  > *"Crea un ModelSerializer para el modelo Producto (nombre, categoria, precio, stock, imagen, imagen_url) que valide que el precio sea mayor a 0, el stock no sea negativo y los textos no estén vacíos, rechazando con código 400. Además implementa los endpoints /api/productos/ y /api/productos/<id>/ con códigos 200, 201, 204, 400 y 404."*
* **Resumen de la respuesta de la IA:**
  Generó la clase `ProductoSerializer(serializers.ModelSerializer)` con métodos `validate_nombre`, `validate_categoria`, `validate_precio` y `validate_stock`, y las vistas genéricas `ListCreateAPIView` y `RetrieveUpdateDestroyAPIView`.
* **Qué se usó o modificó antes de integrarla:**
  Se separaron las vistas de la API en un módulo dedicado `catalogo/api_views.py` para no mezclar las vistas HTML del sitio con los endpoints JSON, y se definieron explícitamente `authentication_classes = [JWTAuthentication]` y `permission_classes = [IsAuthenticatedOrReadOnly]`.

---

### Consulta 3: Recomendaciones de seguridad para autenticación JWT (Requisito ES4)
* **Prompt textual:**
  > *"Dame recomendaciones de seguridad para implementar autenticación JWT con djangorestframework-simplejwt en una API REST: tiempos de expiración y refresco de tokens, permisos por método HTTP, rotación de tokens y protección contra abuso."*
* **Resumen de la respuesta de la IA:**
  Recomendó acotar la vida del `ACCESS_TOKEN_LIFETIME` (15 a 30 minutos), fijar `REFRESH_TOKEN_LIFETIME` en 1 día, activar `ROTATE_REFRESH_TOKENS = True`, exigir prefijo `Bearer` en el encabezado `Authorization`, aplicar `IsAuthenticatedOrReadOnly` para proteger `POST`, `PUT`, `PATCH` y `DELETE`, y agregar *Throttling* (`AnonRateThrottle` y `UserRateThrottle`) para mitigar ataques de fuerza bruta.
* **Qué se usó o modificó antes de integrarla:**
  Se validaron los parámetros en la documentación de SimpleJWT y se aplicaron en `SIMPLE_JWT` y `REST_FRAMEWORK` dentro de `config/settings.py` (`ACCESS_TOKEN_LIFETIME = timedelta(minutes=30)`, `ROTATE_REFRESH_TOKENS = True`, y límites de `100/minute` para anónimos y `300/minute` para usuarios autenticados).

---

### Consulta 4: Generación de Colección de Pruebas de la API y Correcciones Aplicadas (Obligatorio ES4)
* **Prompt textual:**
  > *"Genera una coleccion de requests curl para probar una API DRF en http://localhost:8000/api/productos/ con JWT en /api/token/. Cubre: listado, detalle existente y 404, POST valido e invalido, PUT, DELETE, y POST sin token (debe dar 401). Incluye el codigo de respuesta esperado en cada caso."*
* **Resumen de la respuesta de la IA:**
  Entregó una batería de comandos `curl` y una estructura JSON compatible con Postman/Thunder Client con 11 pruebas que recorren la lectura pública, el intento de creación sin token, la obtención y refresco del JWT, la creación válida e inválida, la edición (`PUT`/`PATCH`) y la eliminación (`DELETE`).
* **Pruebas que fallaron inicialmente y corrección aplicada:**
  1. **Fallo inicial en `POST /api/productos/` sin token:** En la primera prueba devolvió `403 Forbidden` en lugar de `401 Unauthorized` porque DRF evaluaba la sesión del navegador antes que el encabezado `Bearer`. **Corrección:** Se dejó únicamente `JWTAuthentication` en las vistas de la API (`catalogo/api_views.py`), tras lo cual la prueba respondió `401 Unauthorized` como exige la pauta.
  2. **Fallo inicial en `POST /api/productos/` con datos inválidos (`precio: -500`):** En la primera ejecución, el `IntegerField` aceptó números negativos y respondió `201 Created` en lugar de `400 Bad Request`. **Corrección:** Se agregaron las validaciones `validate_precio` (`value <= 0`) y `validate_stock` (`value < 0`) en `catalogo/serializers.py`, logrando que rechace datos inválidos con `400 Bad Request` y detalle en JSON.

---

## Parte 2: Explicación Personal del Proceso

En esta Evaluación Sumativa 4 utilicé la IA como apoyo para implementar la API RESTful de la ferretería con Django REST Framework y asegurarla con tokens JWT. Primero le consulté la configuración base de `djangorestframework` y `simplejwt` para exponer el modelo `Producto` en formato JSON manteniendo las lecturas abiertas al público (`GET`) y bloqueando cualquier modificación (`POST`, `PUT`, `PATCH`, `DELETE`) para usuarios sin token.

Las respuestas de la IA me sirvieron de base para armar las vistas genéricas (`ListCreateAPIView` y `RetrieveUpdateDestroyAPIView`) y la colección de pruebas en `curl` y Postman, pero tuve que corregir dos puntos clave al ejecutar las pruebas reales contra mi servidor local. Primero, cuando probé hacer un `POST` sin token, me di cuenta de que si dejaba la autenticación de sesión activa, Django respondía con código `403` en vez de `401`; lo corregí asignando exclusivamente `JWTAuthentication` en los endpoints de la API. Segundo, tuve que programar manualmente las funciones `validate_precio` y `validate_stock` dentro de `ProductoSerializer` para que la API no dejara pasar precios en cero o negativos y devolviera el código `400 Bad Request` correspondiente.

A través de este trabajo aprendí cómo funciona el ciclo de vida de un token JWT (`access` de corta duración y `refresh` para renovarlo en `/api/token/refresh/`), cómo validar reglas de negocio en un serializer antes de tocar la base de datos y por qué es indispensable probar cada endpoint verificando los códigos de estado HTTP reales.
