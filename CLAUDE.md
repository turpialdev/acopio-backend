# Acopio Venezuela — contexto para agentes

Sistema web de emergencia post-terremoto (Venezuela, 24/06/2026) para coordinar
ayuda humanitaria: un **Directorio público** de centros de acopio y un
**Inventario privado** por centro (libro de movimientos de insumos).

Para el vocabulario de dominio (Centro, Movimiento, Código de gestión, etc.) ver
`claude_context/CONTEXT.md`. Para las decisiones de arquitectura ver los ADR en
`claude_context/000*.md`. Para el contrato de endpoints ver
`claude_context/ENDPOINTS.md`.

## Stack

- **Python 3.13 / Django 6 / Django REST Framework** — backend de endpoints
- **MongoDB** (Atlas) — única base de datos, accedida via `pymongo` directamente
  (sin ORM relacional; `DATABASES = {}`)
- **PyJWT** — autenticación por JWT
- **Railway** — deploy en producción (ver `Procfile`)

## Levantar en local

```bash
source .venv/bin/activate
python manage.py runserver
```

Variables de entorno requeridas en `.env`:

| Variable | Descripción |
|----------|-------------|
| `MONGODB_URI` | URI de conexión a MongoDB Atlas |
| `MONGODB_DB` | Nombre de la base de datos (default: `acopio`) |
| `JWT_SECRET` | Secret para firmar JWT (HS256) |
| `DJANGO_SECRET_KEY` | Secret key de Django |
| `DJANGO_DEBUG` | `True` en local, `False` en producción |

## Estructura del proyecto

```
acopio/          — settings, urls raíz, wsgi, db.py (cliente MongoDB)
api/
  models.py      — nombres de colecciones y valores controlados (enums)
  serializers.py — validación y formato de documentos MongoDB
  views.py       — vistas (APIView + function views)
  urls.py        — rutas de la app
  auth.py        — JWT, hash de códigos, decoradores de auth
claude_context/  — documentación de dominio y decisiones de arquitectura
postman/         — colección Postman con todos los endpoints
```

## Modelo de datos (MongoDB)

Colecciones definidas en `api/models.py`:

| Colección | Descripción |
|-----------|-------------|
| `centros_acopio` | Centro: ficha pública + datos internos del responsable |
| `necesidades` | Una por (centro, categoría); lleva urgencia y detalle libre |
| `catalogo` | Categorías controladas por el Moderador; `es_insumo` distingue bienes de no-bienes |
| `movimientos` | Libro de entradas/salidas por centro (ADR 0007: sin saldo de existencias) |
| `codigos_gestion` | Códigos de acceso; se guarda el hash SHA-256, nunca el texto plano |
| `moderadores` | Cuentas reales del equipo de moderación |
| `reportes` | Reportes ciudadanos de centros falsos/duplicados/peligrosos |
| `contactos_emergencia` | Directorio público de organismos de socorro (P5) |

## Auth (ADR 0002)

- **Código de gestión:** formato `{PREFIJO}{8 dígitos}` — `CE12345678` para centros
  (responsable), `VL12345678` para voluntarios. Se almacena como SHA-256; nunca
  el texto plano. Generado con `generar_codigo(prefijo)` en `api/auth.py`, que
  reintenta si hay colisión. Se canjea por JWT en `POST /api/auth/codigo/`.
- **Moderador:** cuenta real (email + password hasheado con Django's `make_password`).
  JWT via `POST /api/auth/moderador/`. El primer moderador se siembra directo en DB.
- **JWT:** HS256, 30 días. Payload de código: `tipo`, `centro_id`, `rol`,
  `codigo_id`, `etiqueta`. Payload de moderador: `tipo`, `moderador_id`, `nombre`.
- **Decoradores** en `api/auth.py`: `@require_codigo`, `@require_responsable`,
  `@require_moderador`. Usar `check_centro(request, pk)` para verificar que el
  `centro_id` del token coincida con el `pk` de la URL.

## Convenciones de código

- Las vistas son `APIView` con métodos `get/post/patch/delete`.
- `format_doc(doc)` convierte `_id` → `id` (string) en todos los documentos.
- `_get_doc(collection, pk)` encapsula la lookup con manejo de 400/404.
- Los endpoints del directorio público no llevan auth (`AllowAny`).
- Los endpoints protegidos usan los decoradores de `api/auth.py`, no
  `permission_classes` de DRF.
- No usar migraciones Django (no hay DB relacional). Los índices se crean con
  `ensure_indexes()` en `api/models.py`.
- Las vistas del panel de gestión viven en `api/views.py` bajo el comentario
  `# ---- Panel de gestión del centro ----`. Las del panel de moderación en
  `api/mod_views.py` y sus rutas en `api/mod_urls.py`.

## Estado de implementación

**Todo implementado.** Las historias P1–P5, R1–R8, V1–V4 y M1–M9 están cubiertas.

### Directorio público (`api/urls.py`)
- `GET /api/centros/` — listar centros (filtra ocultos; params: `q`, `estado`, `municipio`, `categoria`, `urgencia`)
- `POST /api/centros/` — registrar centro; devuelve `codigo_raiz` una sola vez
- `GET /api/centros/{id}/` — ficha pública (404 si oculto)
- `POST /api/centros/{id}/reportar/` — reporte ciudadano a cola de moderación
- `GET /api/contactos-emergencia/` — directorio de organismos de socorro (params: `zona`, `tipo`)
- `GET /api/catalogo/` — categorías (params: `es_insumo`, `activa`)
- `GET/PATCH/DELETE /api/catalogo/{id}/`

### Panel de gestión — responsable y voluntario (`api/urls.py`, JWT código)
- `GET/PATCH /api/centros/{id}/ficha/` — ficha privada con necesidades; PATCH solo responsable
- `GET/POST /api/centros/{id}/movimientos/` — libro de movimientos (params: `tipo`, `categoria_id`)
- `PATCH/DELETE /api/centros/{id}/movimientos/{mov_id}/` — corregir/anular (voluntario: solo propios, ventana 1h)
- `GET /api/centros/{id}/totales/` — totales derivados por categoría (no existencias reales, ADR 0007)
- `GET/POST /api/centros/{id}/codigos/` — listar/crear códigos de voluntario; solo responsable
- `DELETE /api/centros/{id}/codigos/{cod_id}/` — revocar código de voluntario; solo responsable
- `GET /api/centros/{id}/sugerencias/` — señales del inventario (salidas > entradas hoy, ADR 0005)
- `GET/POST /api/necesidades/` y `GET/PATCH/DELETE /api/necesidades/{id}/`
- `GET/POST /api/movimientos/` y `GET/PATCH/DELETE /api/movimientos/{id}/` — endpoints planos (misma lógica, sin `centro_pk` en URL)

### Auth
- `POST /api/auth/codigo/` — canjear código → JWT
- `POST /api/auth/moderador/` — login moderador → JWT

### Panel de moderación (`api/mod_urls.py`, bajo `/api/mod/`, JWT moderador)
- `GET /api/mod/cola/` — centros sin_verificar + reportes pendientes
- `GET /api/mod/centros/` — todos los centros (incluyendo ocultos)
- `POST /api/mod/centros/` — crear centro (nace verificado)
- `GET/PATCH /api/mod/centros/{id}/`
- `POST /api/mod/centros/{id}/verificar/` y `/ocultar/`
- `POST /api/mod/centros/{id}/reemitir-codigo/` — revoca código raíz activo y emite uno nuevo
- `POST /api/mod/centros/fusionar/` — fusiona dos centros; migra movimientos, códigos y necesidades
- `GET /api/mod/reportes/` y `POST /api/mod/reportes/{id}/resolver/`
- `GET/POST /api/mod/catalogo/` y `PATCH /api/mod/catalogo/{id}/`
- `GET/POST /api/mod/moderadores/` y `DELETE /api/mod/moderadores/{id}/`
- `GET /api/mod/metricas/`
- `GET/POST /api/mod/contactos-emergencia/` y `PATCH/DELETE /api/mod/contactos-emergencia/{id}/`

**Pendiente:**
- Paginación en listados
- PWA / Directorio offline (P6)

## Restricciones no negociables

- Guardar **hash** del código, nunca el texto plano.
- El Directorio no muestra centros `oculto`.
- El Inventario es un libro de movimientos — **nunca almacenar saldo de existencias** (ADR 0007).
- La urgencia de la ficha la declara el humano; el inventario **sugiere**, no publica (ADR 0005).
- El código raíz (`CE…`) se devuelve **una sola vez** al crear el centro.
