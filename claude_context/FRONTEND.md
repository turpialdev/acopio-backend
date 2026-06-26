# Guía de integración — Frontend

Esta guía cubre cómo conectar cada pantalla del Figma a los endpoints del backend.
La URL base en producción sale de Railway; en local es `http://localhost:8000`.

---

## Configuración base

```js
const BASE_URL = process.env.NEXT_PUBLIC_API_URL // ej: https://acopio-backend.up.railway.app

async function api(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    ...options,
  })
  if (!res.ok) throw await res.json()
  return res.status === 204 ? null : res.json()
}
```

El token JWT se guarda en `localStorage`. Dura 30 días.
El payload decodificado contiene `tipo`, `centro_id`, `rol`, `codigo_id`, `etiqueta`
(para código de gestión) o `tipo`, `moderador_id`, `nombre` (para moderador).

---

## Pantalla: Directorio público

### Cargar categorías para los pills de filtro

```
GET /api/catalogo/?es_insumo=true&activa=true
```

```js
const categorias = await api('/api/catalogo/?es_insumo=true&activa=true')
// [{id, nombre, es_insumo, activa}, ...]
```

### Buscar centros

```
GET /api/centros/?q=&estado=&municipio=&categoria=<id>&urgencia=
```

| Param | Descripción |
|-------|-------------|
| `q` | Texto libre sobre el nombre del centro |
| `estado` | Estado de Venezuela (ej. `Miranda`) |
| `municipio` | Municipio (ej. `Chacao`) |
| `categoria` | `id` de una categoría — filtra centros que la tengan como necesidad |
| `urgencia` | `urgente` / `media` / `leve` |

Respuesta por centro:

```json
{
  "id": "...",
  "nombre": "Dispensario San Martín",
  "estado": "Miranda",
  "municipio": "Chacao",
  "direccion": "Calle Venezuela...",
  "contacto": "0414 12345678",
  "ubicacion_url": "https://maps.google.com/...",
  "lat": 10.48,
  "lng": -66.87,
  "estado_verificacion": "verificado",
  "actualizado_en": "2026-06-24T10:25:00Z",
  "urgencia_maxima": "urgente",
  "necesidades": [
    {
      "id": "...",
      "categoria_id": "...",
      "categoria_nombre": "Agua Potable",
      "urgencia": "urgente",
      "detalle": "en botellas"
    }
  ]
}
```

- Badge **Verificado / Sin verificar**: campo `estado_verificacion`
- Sección "Insumos requeridos": array `necesidades`; cada ítem es un tag `{categoria_nombre} / {detalle}`
- "ULTIMA ACTUALIZACIÓN": `actualizado_en` formateado
- Botón "Como llegar": abre `ubicacion_url`
- Botón "Llamar": `tel:{contacto}` — solo visible si `contacto` tiene valor
- Color del borde: `urgencia_maxima` (`urgente`=rojo, `media`=naranja, `leve`=gris, `null`=sin borde)

### Contactos de emergencia

```
GET /api/contactos-emergencia/?zona=Miranda
```

```json
[
  {
    "id": "...",
    "nombre": "Cruz Roja Venezuela",
    "tipo": "Emergencias nacionales",
    "zona": "Nacional",
    "telefonos": ["0212-9057777"],
    "whatsapp_url": null
  }
]
```

- `tipo` es el subtítulo que aparece bajo el nombre
- Botón "Llamar": `tel:{telefonos[0]}`
- El panel se muestra/oculta con estado local; la petición se hace solo al abrir

---

## Pantalla: Registrar centro

Flujo de tres pasos porque el JWT se necesita para crear la necesidad inicial.

### Paso 1 — Crear centro

```
POST /api/centros/
```

```json
{
  "nombre": "Centro Comunitario La Vega",
  "estado": "Miranda",
  "municipio": "Libertador",
  "direccion": "Calle 5, sector Los Pinos",
  "nombre_responsable": "Juan Pérez",
  "telefono_responsable": "+58 212 000-0000",
  "cargo_responsable": "director"
}
```

Valores válidos para `cargo_responsable`: `propietario` / `socio` / `director` / `gerente`

Respuesta — incluye `codigo_raiz` que **debe mostrarse una sola vez** al usuario:

```json
{
  "id": "...",
  "nombre": "...",
  "codigo_raiz": "CE82907029"
}
```

El código tiene formato `CE` + 8 dígitos. Pedirle al usuario que lo guarde antes de continuar.

### Paso 2 — Canjear código por JWT

```
POST /api/auth/codigo/
{ "codigo": "CE82907029" }
```

```json
{
  "token": "eyJ...",
  "rol": "responsable",
  "centro_id": "...",
  "etiqueta": "Responsable"
}
```

Guardar `token` y `centro_id` en `localStorage`.

### Paso 3 — Crear necesidad con la categoría principal

```
POST /api/necesidades/
Authorization: Bearer {token}

{
  "centro_id": "{centro_id}",
  "categoria_id": "{id del dropdown}",
  "urgencia": "media"
}
```

---

## Pantalla: Login (código de acceso)

```
POST /api/auth/codigo/
{ "codigo": "CE82907029" }   // o VL64829772 para voluntario
```

- `rol === 'responsable'` → redirigir al panel completo
- `rol === 'voluntario'` → redirigir solo al inventario
- Error 401 → código inválido o revocado

```js
const { token, rol, centro_id } = await api('/api/auth/codigo/', {
  method: 'POST',
  body: JSON.stringify({ codigo }),
})
localStorage.setItem('token', token)
localStorage.setItem('centro_id', centro_id)
localStorage.setItem('rol', rol)
```

---

## Pantalla: Panel del responsable — ficha

```
GET  /api/centros/{centro_id}/ficha/
PATCH /api/centros/{centro_id}/ficha/
Authorization: Bearer {token_responsable}
```

El GET devuelve la ficha completa con datos internos (nombre_responsable, etc.) más necesidades enriquecidas con `categoria_nombre`.

El PATCH acepta campos de la ficha y opcionalmente `necesidades` (reemplaza el array completo):

```json
{
  "vialidad": "Acceso por Autopista Prados del Este",
  "necesidades": [
    { "categoria_id": "{id}", "urgencia": "urgente", "detalle": "Agua en botellas de 1.5L" },
    { "categoria_id": "{id}", "urgencia": "media",   "detalle": "Ropa para adultos" }
  ]
}
```

`estado_verificacion` es inmutable desde este endpoint.

---

## Pantalla: Inventario de movimientos (voluntario y responsable)

### Registrar un movimiento

```
POST /api/centros/{centro_id}/movimientos/
Authorization: Bearer {token}
```

El `centro_id` viene del JWT — no se envía en el body.

**Ingreso de insumos:**
```json
{
  "categoria_id": "{id}",
  "tipo": "entrada",
  "cantidad": 15,
  "unidad": "kg",
  "nota": "descripción breve",
  "contraparte": "Nombre del donante o entidad"
}
```

**Salida de insumos:**
```json
{
  "categoria_id": "{id}",
  "tipo": "salida",
  "cantidad": 3,
  "unidad": "cajas",
  "contraparte": "Nombre del beneficiado"
}
```

Solo categorías con `es_insumo: true` son válidas. El dropdown se puebla con:
```
GET /api/catalogo/?es_insumo=true&activa=true
```

### Ver historial de movimientos

```
GET /api/centros/{centro_id}/movimientos/
GET /api/centros/{centro_id}/movimientos/?tipo=entrada
GET /api/centros/{centro_id}/movimientos/?tipo=salida
GET /api/centros/{centro_id}/movimientos/?categoria_id={id}
```

Respuesta (ordenada por `registrado_en` desc):

```json
[
  {
    "id": "...",
    "centro_id": "...",
    "categoria_id": "...",
    "tipo": "entrada",
    "cantidad": 15,
    "unidad": "kg",
    "nota": "descripción",
    "contraparte": "Juan",
    "registrado_por": "Ana - Puerta",
    "registrado_en": "2026-06-25T10:32:00Z"
  }
]
```

Lógica de display para cada fila:
- **Chip tipo**: `tipo === 'entrada'` → verde "ENTRADA"; `'salida'` → azul oscuro "SALIDA"
- **"Ana – Juan"**: `{registrado_por} – {contraparte}` (omitir el guion si `contraparte` es null)
- **Botón "Corregir"**: visible si `rol === 'voluntario'` y `registrado_en` tiene menos de **1 hora**. Si el PATCH devuelve 403, mostrar candado 🔒
- **Responsable**: puede corregir cualquier movimiento del centro sin límite de tiempo
- **Sección "HOY"**: agrupar por fecha de `registrado_en` en zona horaria local
- **Sección "REGISTROS ANTERIORES"**: movimientos de días anteriores

### Corregir un movimiento

```
PATCH /api/centros/{centro_id}/movimientos/{mov_id}/
Authorization: Bearer {token}

{ "cantidad": 20, "unidad": "L", "nota": "corregido" }
```

`centro_id`, `categoria_id` y `tipo` son inmutables. Solo se envían los campos que cambian.

Errores posibles:
- `403` `"Solo puedes modificar tus propios registros."` — voluntario editando movimiento ajeno
- `403` `"Solo puedes modificar registros de la última hora."` → mostrar candado 🔒

### Totales del inventario

```
GET /api/centros/{centro_id}/totales/
Authorization: Bearer {token}
```

```json
{
  "nota": "Totales registrados — no representan existencias reales (ADR 0007)",
  "categorias": [
    { "categoria_id": "...", "categoria_nombre": "Agua Potable", "entradas": 55.0, "salidas": 20.0 }
  ]
}
```

Estos totales son **registrados**, no de existencias. No implica que haya 35L disponibles.

---

## Pantalla: Sugerencias del inventario (responsable)

```
GET /api/centros/{centro_id}/sugerencias/
Authorization: Bearer {token}
```

```json
{
  "sugerencias": [
    {
      "categoria_id": "...",
      "categoria_nombre": "Agua Potable",
      "entradas_hoy": 20,
      "salidas_hoy": 45,
      "urgencia_actual": "media",
      "mensaje": "Hoy salió más Agua Potable del que entró. Considera revisar la urgencia en la ficha."
    }
  ]
}
```

Mostrar solo si `sugerencias.length > 0`. No auto-actualiza la ficha — el responsable decide.

---

## Pantalla: Códigos de voluntario (responsable)

### Listar códigos activos

```
GET /api/centros/{centro_id}/codigos/
Authorization: Bearer {token_responsable}
```

```json
[{ "id": "...", "etiqueta": "Juan - Puerta", "rol": "voluntario", "revocado_en": null }]
```

### Crear código

```
POST /api/centros/{centro_id}/codigos/
Authorization: Bearer {token_responsable}

{ "etiqueta": "María - Almacén" }
```

```json
{
  "id": "...",
  "etiqueta": "María - Almacén",
  "rol": "voluntario",
  "codigo": "VL64829772"   ← texto plano, entregar al voluntario; no se muestra de nuevo
}
```

El código tiene formato `VL` + 8 dígitos (`VL` evita confusión O/0 de `VO`).

### Revocar código

```
DELETE /api/centros/{centro_id}/codigos/{cod_id}/
Authorization: Bearer {token_responsable}
→ 204 No Content
```

El código revocado no puede autenticarse. Segunda revocación devuelve 400.

---

## Panel de moderador

### Login

```
POST /api/auth/moderador/
{ "email": "mod@acopio.ve", "password": "..." }
→ { "token": "...", "moderador_id": "...", "nombre": "..." }
```

### Cola de trabajo

```
GET /api/mod/cola/
→ { "centros_sin_verificar": [...], "reportes_pendientes": [...] }
```

### Verificar / ocultar / editar centro

```
POST /api/mod/centros/{id}/verificar/
POST /api/mod/centros/{id}/ocultar/
GET/PATCH /api/mod/centros/{id}/
```

### Reemitir código raíz (recuperación)

```
POST /api/mod/centros/{id}/reemitir-codigo/
→ { "codigo_raiz": "CE12345678" }
```

Revoca el código raíz anterior automáticamente.

### Fusionar centros duplicados

```
POST /api/mod/centros/fusionar/
{ "centro_a": "{id}", "centro_b": "{id}", "conservar": "{id_a_conservar}" }
→ { "conservado": {...}, "descartado_id": "..." }
```

### Reportes ciudadanos

```
GET /api/mod/reportes/?estado=pendiente
POST /api/mod/reportes/{id}/resolver/
```

### Gestionar contactos de emergencia

```
GET    /api/mod/contactos-emergencia/
POST   /api/mod/contactos-emergencia/
PATCH  /api/mod/contactos-emergencia/{id}/
DELETE /api/mod/contactos-emergencia/{id}/
```

```json
{
  "nombre": "Cruz Roja Venezuela",
  "tipo": "Emergencias nacionales",
  "zona": "Nacional",
  "telefonos": ["0212-9057777", "0800-SOCORRO"],
  "whatsapp_url": "https://wa.me/58212..."
}
```

### Catálogo

```
GET/POST /api/mod/catalogo/
PATCH /api/mod/catalogo/{id}/     { "activa": false }
```

### Moderadores

```
GET/POST /api/mod/moderadores/    { "nombre": "...", "email": "...", "password": "..." }
DELETE /api/mod/moderadores/{id}/
```

### Métricas

```
GET /api/mod/metricas/
→ { "centros": { "total": 16, "verificados": 7, "sin_verificar": 9, "ocultos": 3 },
    "necesidades_urgentes": 7, "movimientos_total": 14 }
```

---

## Manejo de errores

| HTTP | Significado | Acción sugerida |
|------|-------------|-----------------|
| `400` | Validación fallida | Mostrar `detail` o campos con error debajo del input |
| `401` | Token ausente / código inválido | Redirigir a login |
| `403` | Sin permisos (centro incorrecto, voluntario fuera de ventana) | Mostrar mensaje inline |
| `404` | Recurso no existe | Pantalla de error |

Errores de validación de campos:
```json
{ "nombre": ["Este campo es requerido."], "estado": ["Este campo es requerido."] }
```

Errores generales:
```json
{ "detail": "Código inválido o revocado." }
```

---

## Estados controlados (enums)

Usar exactamente estas cadenas al enviar:

| Campo | Valores |
|-------|---------|
| `tipo` (movimiento) | `entrada` / `salida` |
| `urgencia` | `urgente` / `media` / `leve` |
| `cargo_responsable` | `propietario` / `socio` / `director` / `gerente` |
| `estado_verificacion` | `sin_verificar` / `verificado` / `oculto` |
| `motivo` (reporte) | `duplicado` / `falso` / `peligroso` / `otro` |

## Formato de códigos

| Tipo | Formato | Ejemplo |
|------|---------|---------|
| Código raíz (responsable) | `CE` + 8 dígitos | `CE82907029` |
| Código de voluntario | `VL` + 8 dígitos | `VL64829772` |

`VL` en lugar de `VO` para evitar confusión entre la letra O y el número 0.
