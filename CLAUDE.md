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

## Auth (ADR 0002)

- **Código de gestión:** cadena opaca aleatoria (`secrets.token_urlsafe(32)`).
  Se almacena como SHA-256. El rol (`responsable | voluntario`) vive en el
  servidor, no en el código. Se canjea por un JWT en `POST /api/auth/codigo/`.
- **Moderador:** cuenta real (email + password hasheado). JWT via
  `POST /api/auth/moderador/`.
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

## Estado de implementación

**Implementado:**
- `GET/POST /api/centros/` — listar y crear centros (POST devuelve `codigo_raiz`)
- `GET/PATCH/DELETE /api/centros/{pk}/` — ficha de centro
- `GET/POST /api/catalogo/` y `GET/PATCH/DELETE /api/catalogo/{pk}/`
- `GET/POST /api/necesidades/` y `GET/PATCH/DELETE /api/necesidades/{pk}/`
- `GET/POST /api/movimientos/` y `GET/PATCH/DELETE /api/movimientos/{pk}/`
- `POST /api/auth/codigo/` — canjear código → JWT
- `POST /api/auth/moderador/` — login moderador → JWT

**Pendiente (MVP):**
- Proteger con auth los endpoints del panel de gestión
- Reestructurar URLs del panel de gestión bajo `/api/centros/{id}/...`
- Filtrar centros ocultos del directorio público
- `POST /api/centros/{id}/reportar/`
- Endpoints del panel de moderación (`/api/mod/...`)
- Paginación en listados

**Deseable (post-MVP):**
- Señales del inventario → sugerir actualizar ficha (ADR 0005)
- Contactos de emergencia en home
- PWA / Directorio offline
- Métricas básicas

## Restricciones no negociables

- Guardar **hash** del código, nunca el texto plano.
- El Directorio no muestra centros `oculto`.
- El Inventario es un libro de movimientos — **nunca almacenar saldo de existencias** (ADR 0007).
- La urgencia de la ficha la declara el humano; el inventario **sugiere**, no publica (ADR 0005).
- El código raíz se devuelve **una sola vez** al crear el centro.
