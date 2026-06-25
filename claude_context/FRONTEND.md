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

El token JWT se guarda en `localStorage` (o sessionStorage). Dura 30 días.
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
// Render pills: [{id, nombre, es_insumo, activa}, ...]
```

### Buscar centros

```
GET /api/centros/?q=&estado=&municipio=&categoria=<id>&urgencia=
```

Parámetros opcionales:

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
- Sección "Insumos requeridos": array `necesidades` — cada ítem es un tag `{categoria_nombre} / {detalle}`
- "ULTIMA ACTUALIZACIÓN": `actualizado_en` formateado
- Botón "Como llegar": abre `ubicacion_url`
- Botón "Llamar": `tel:{contacto}` — solo visible si `contacto` tiene valor
- "Urgencia máxima" para el color del borde: `urgencia_maxima` (`urgente`=rojo, `media`=naranja, `leve`=gris)

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

- El campo `tipo` es el subtítulo que aparece bajo el nombre
- Botón "Llamar": `tel:{telefonos[0]}`
- El panel se muestra/oculta con estado local; la petición se hace solo al abrir

---

## Pantalla: Registrar centro

Flujo de dos pasos porque el JWT se necesita para crear la necesidad.

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

Respuesta incluye `codigo_raiz` (mostrar UNA SOLA VEZ y pedir al usuario que lo copie):

```json
{
  "id": "...",
  "nombre": "...",
  "codigo_raiz": "xK9mT2..."
}
```

### Paso 2 — Canjear código por JWT

```
POST /api/auth/codigo/
{ "codigo": "xK9mT2..." }
```

```json
{
  "token": "eyJ...",
  "rol": "responsable",
  "centro_id": "...",
  "etiqueta": ""
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
{ "codigo": "AX-1234-5678-0" }
```

- Si el código es de **responsable**: `rol === 'responsable'` → redirigir al panel completo
- Si es de **voluntario**: `rol === 'voluntario'` → redirigir solo al inventario
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

## Pantalla: Inventario de movimientos (voluntario y responsable)

### Registrar un movimiento

```
POST /api/movimientos/
Authorization: Bearer {token}
```

El `centro_id` viene del JWT — no se envía en el body.

**Ingreso de insumos:**
```json
{
  "categoria_id": "{id del dropdown}",
  "tipo": "entrada",
  "cantidad": 15,
  "unidad": "kg",
  "nota": "descripción breve del insumo",
  "contraparte": "Nombre del donante o entidad"
}
```

**Salida de insumos:**
```json
{
  "categoria_id": "{id del dropdown}",
  "tipo": "salida",
  "cantidad": 3,
  "unidad": "cajas",
  "contraparte": "Nombre del beneficiado"
}
```

Solo categorías con `es_insumo: true` son válidas. El dropdown de "Insumo" se puebla con:
```
GET /api/catalogo/?es_insumo=true&activa=true
```

### Ver historial de movimientos

```
GET /api/movimientos/
GET /api/movimientos/?tipo=entrada
GET /api/movimientos/?tipo=salida
GET /api/movimientos/?categoria_id={id}
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
    "registrado_por": "Ana",
    "registrado_en": "2026-06-25T10:32:00Z"
  }
]
```

Lógica de display para cada fila:
- **Etiqueta tipo**: `tipo === 'entrada'` → chip verde "ENTRADA"; `'salida'` → chip azul oscuro "SALIDA"
- **"Juan – Puerta"**: `{registrado_por} – {contraparte}` (omitir el guion si `contraparte` es null)
- **Botón "Corregir"**: visible si `rol === 'voluntario'` y `registrado_en` tiene menos de 30 minutos. Si el PATCH devuelve 403, mostrar "Bloqueado".
- **Sección "HOY"**: agrupar por fecha de `registrado_en` en la zona horaria local
- **Sección "REGISTROS ANTERIORES"**: movimientos de días anteriores

### Corregir un movimiento

```
PATCH /api/movimientos/{id}/
Authorization: Bearer {token}

{ "cantidad": 20, "unidad": "L", "nota": "corregido" }
```

`centro_id` y `categoria_id` son inmutables. Solo se envían los campos que cambian.

Errores posibles:
- `403` `"Solo puedes corregir tus propios registros."` — voluntario intentando editar movimiento ajeno
- `403` `"Solo puedes corregir registros de los últimos 30 minutos."` → mostrar candado 🔒

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
Authorization: Bearer {token_moderador}
→ { "centros_sin_verificar": [...], "reportes_pendientes": [...] }
```

### Verificar / ocultar centro

```
POST /api/mod/centros/{id}/verificar/
POST /api/mod/centros/{id}/ocultar/
```

### Gestionar contactos de emergencia

```
GET    /api/mod/contactos-emergencia/
POST   /api/mod/contactos-emergencia/
PATCH  /api/mod/contactos-emergencia/{id}/
DELETE /api/mod/contactos-emergencia/{id}/
```

Body para crear/editar:
```json
{
  "nombre": "Cruz Roja Venezuela",
  "tipo": "Emergencias nacionales",
  "zona": "Nacional",
  "telefonos": ["0212-9057777", "0800-SOCORRO"],
  "whatsapp_url": "https://wa.me/58212..."
}
```

---

## Manejo de errores

| HTTP | Significado | Acción sugerida |
|------|-------------|-----------------|
| `400` | Validación fallida | Mostrar `detail` o campos con error debajo del input |
| `401` | Token ausente / código inválido | Redirigir a login |
| `403` | Sin permisos (centro incorrecto, voluntario fuera de ventana) | Mostrar mensaje inline |
| `404` | Recurso no existe | Pantalla de error |

Los errores de validación de campos vienen como objeto:
```json
{ "nombre": ["Este campo es requerido."], "estado": ["Este campo es requerido."] }
```

Los errores generales vienen como:
```json
{ "detail": "Código inválido o revocado." }
```

---

## Estados controlados (enums)

Estos valores son fijos — usar exactamente estas cadenas al enviar:

| Campo | Valores |
|-------|---------|
| `tipo` (movimiento) | `entrada` / `salida` |
| `urgencia` | `urgente` / `media` / `leve` |
| `cargo_responsable` | `propietario` / `socio` / `director` / `gerente` |
| `estado_verificacion` | `sin_verificar` / `verificado` / `oculto` |
| `motivo` (reporte) | `duplicado` / `falso` / `peligroso` / `otro` |
