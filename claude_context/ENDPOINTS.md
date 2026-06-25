# Contrato de endpoints — Acopio Venezuela

Documento de referencia para el equipo. El vocabulario es el de `CONTEXT.md`.

## Decisiones de diseño

- **Auth:** JWT en todos los endpoints protegidos. Dos flujos de obtención:
  canjear un código de gestión (`POST /api/auth/codigo/`) o hacer login de
  moderador (`POST /api/auth/moderador/`). El payload del token incluye
  `centro_id` y `rol` (`responsable | voluntario`) para el flujo de gestión, o
  `moderador_id` para el flujo de moderación.
- **`centro_id` en la URL:** los endpoints del panel de gestión usan
  `/api/centros/{id}/...`. El middleware verifica que el `centro_id` del JWT
  coincida con el `{id}` de la URL.
- **Acciones explícitas:** las transiciones de estado se hacen con verbos propios
  (`/verificar/`, `/ocultar/`) en lugar de un `PATCH` genérico con un valor
  libre, para evitar transiciones arbitrarias.
- **Códigos de gestión:** se almacena el hash, nunca el texto plano. El código
  raíz se devuelve una sola vez al crear el centro.

---

## 1. Directorio público — sin auth

| Método | Ruta | Historia |
|--------|------|----------|
| `GET` | `/api/centros/` | P1 — Listar y filtrar centros. Query params: `texto`, `estado`, `municipio`, `categoria`, `urgencia`. Solo devuelve centros no ocultos. |
| `GET` | `/api/centros/{id}/` | P2 — Ver ficha de un centro. |
| `POST` | `/api/centros/{id}/reportar/` | P4 — Reportar centro falso/duplicado/peligroso. Va a cola de moderación; no oculta el centro. |
| `GET` | `/api/catalogo/` | — Listar categorías activas (para alimentar los filtros y el formulario de necesidades). |
| `GET` | `/api/contactos-emergencia/` | P5 — *(deseable)* Contactos de emergencia curados por el moderador. |

---

## 2. Alta de centro — sin auth

| Método | Ruta | Historia |
|--------|------|----------|
| `POST` | `/api/centros/` | R1 — Crear centro. El centro nace `sin_verificar` pero visible. La respuesta incluye el **código raíz una sola vez**; después no se puede recuperar sin intervención del moderador. |

---

## 3. Auth — obtención de JWT

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/auth/codigo/` | R2, V1 — Canjear código de gestión. Devuelve JWT con `centro_id`, `rol` y `etiqueta`. |
| `POST` | `/api/auth/moderador/` | — Login de moderador (usuario + contraseña). Devuelve JWT con `moderador_id`. |

---

## 4. Panel de gestión del centro — JWT de código de gestión

El middleware verifica que `centro_id` del token coincida con el `{id}` de la URL.
Las restricciones de rol (`responsable` vs `voluntario`) se aplican en cada vista.

| Método | Ruta | Rol mínimo | Historia |
|--------|------|------------|----------|
| `GET` | `/api/centros/{id}/ficha/` | voluntario | — Ver la ficha propia con campos internos del responsable. |
| `PATCH` | `/api/centros/{id}/ficha/` | responsable | R3 — Editar ficha pública y lista de necesidades. Refresca `actualizado_en`. |
| `GET` | `/api/centros/{id}/movimientos/` | voluntario | R5, V4 — Listar libro de movimientos. Query params: `tipo` (`entrada|salida`), `categoria`. Paginado. |
| `POST` | `/api/centros/{id}/movimientos/` | voluntario | R4, V2 — Registrar una entrada o salida. El `registrado_por` se toma del JWT. |
| `PATCH` | `/api/centros/{id}/movimientos/{mov_id}/` | voluntario* | R5, V3 — Corregir un movimiento. *Voluntario: solo propios recientes. Responsable: cualquiera. |
| `DELETE` | `/api/centros/{id}/movimientos/{mov_id}/` | voluntario* | R5 — Anular un movimiento. Mismas restricciones que corregir. |
| `GET` | `/api/centros/{id}/totales/` | voluntario | — Totales derivados por categoría, etiquetados como "registrado" (no existencia). |
| `GET` | `/api/centros/{id}/codigos/` | responsable | R6 — Listar códigos de voluntario activos y revocados. |
| `POST` | `/api/centros/{id}/codigos/` | responsable | R6 — Crear código de voluntario con etiqueta. Devuelve el código una sola vez. |
| `DELETE` | `/api/centros/{id}/codigos/{cod_id}/` | responsable | R6 — Revocar código de voluntario. |

---

## 5. Panel de moderación — JWT de moderador

Todos los endpoints bajo `/api/mod/` requieren JWT de moderador.

### Centros

| Método | Ruta | Historia |
|--------|------|----------|
| `GET` | `/api/mod/centros/` | — Listar todos los centros (incluyendo `oculto`). Mismos filtros que el directorio público más `estado_verificacion`. |
| `POST` | `/api/mod/centros/` | M7 — Crear centro. Nace `verificado` directamente; no entra a la cola. |
| `GET` | `/api/mod/centros/{id}/` | — Ver cualquier centro con todos sus campos internos. |
| `PATCH` | `/api/mod/centros/{id}/` | M7 — Editar cualquier campo de cualquier centro. |
| `POST` | `/api/mod/centros/{id}/verificar/` | M2 — Marcar centro como `verificado`. |
| `POST` | `/api/mod/centros/{id}/ocultar/` | M2 — Marcar centro como `oculto`. |
| `POST` | `/api/mod/centros/{id}/reemitir-codigo/` | M4 — Revocar el código raíz actual y emitir uno nuevo. Devuelve el nuevo código una sola vez. |
| `POST` | `/api/mod/centros/fusionar/` | M3 — Fusionar dos centros duplicados. Body: `{ centro_a: id, centro_b: id, conservar: id }`. |

### Cola y reportes

| Método | Ruta | Historia |
|--------|------|----------|
| `GET` | `/api/mod/cola/` | M1 — Centros `sin_verificar` + reportes pendientes. Ordenable por urgencia y fecha. |
| `GET` | `/api/mod/reportes/` | — Listar reportes ciudadanos (filtrable por `estado`: `pendiente|resuelto`). |
| `POST` | `/api/mod/reportes/{id}/resolver/` | — Marcar reporte como resuelto. |

### Catálogo

| Método | Ruta | Historia |
|--------|------|----------|
| `GET` | `/api/mod/catalogo/` | M5 — Listar todas las categorías (activas e inactivas). |
| `POST` | `/api/mod/catalogo/` | M5 — Crear categoría. Campos: `nombre`, `es_insumo`, `activa`. |
| `PATCH` | `/api/mod/catalogo/{id}/` | M5 — Editar categoría (nombre, `es_insumo`, `activa`). |

### Moderadores y métricas

| Método | Ruta | Historia |
|--------|------|----------|
| `GET` | `/api/mod/moderadores/` | M6 — Listar cuentas de moderador. |
| `POST` | `/api/mod/moderadores/` | M6 — Crear cuenta de moderador. |
| `DELETE` | `/api/mod/moderadores/{id}/` | M6 — Desactivar cuenta de moderador. |
| `GET` | `/api/mod/metricas/` | M8 — *(deseable)* Centros por estado federal, urgentes activos, movimientos por día. |

---

## Resumen de conteo

| Superficie | Endpoints MVP | Endpoints deseables |
|------------|:---:|:---:|
| Directorio público | 3 | 1 |
| Alta de centro | 1 | — |
| Auth | 2 | — |
| Panel de gestión | 10 | — |
| Panel de moderación | 14 | 1 |
| **Total** | **30** | **2** |
