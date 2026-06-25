# Arquitectura funcional — Acopio Venezuela

Documento de **forma funcional y contratos**, no de herramientas. La elección de
lenguaje, framework y base de datos es del equipo (ver ADR 0003); aquí se fija
qué debe existir y qué restricciones debe cumplir, sea cual sea el stack.

Para el vocabulario, ver `CONTEXT.md`. Para el porqué de cada decisión, los ADR
en `docs/adr/`.

---

## 1. Actores

- **Público** (sin autenticación): consulta el Directorio.
- **Responsable de centro** (código raíz): gestiona ficha, inventario y códigos.
- **Voluntario** (código creado por el responsable): registra movimientos.
- **Moderador** (cuenta real): cura el Directorio y administra la plataforma.

## 2. Forma del sistema

**Una sola aplicación desplegable** (backend de múltiples endpoints + front
responsive) sobre **una sola base de datos**. No microservicios (ADR 0003). Tres
superficies sobre la misma app:

1. **Directorio público** — lectura sin login. Ultraligero (presupuesto de §6).
2. **Panel de gestión del centro** — detrás del código de gestión (ADR 0002).
3. **Panel de moderación/administración** — detrás de cuenta de moderador.

## 3. Modelo de dominio (entidades y campos clave)

**Centro**
- `id`, `nombre`
- `estado` (entidad federal), `municipio`, `direccion` (texto libre)
- `contacto` (teléfono público, opcional), `ubicacion_url` (link de Maps, opcional)
- `vialidad` (texto libre, opcional)
- `estado_verificacion`: `sin_verificar | verificado | oculto`
- `actualizado_en` (timestamp de la última edición de la ficha)
- **Datos internos del responsable (no se muestran en el Directorio):**
  `nombre_responsable`, `telefono_responsable` (sirve además de contacto de
  recuperación), `cargo_responsable`: `propietario | socio | director | gerente`

**Necesidad** (línea de la ficha; ver ADR 0006)
- `centro_id`, `categoria_id` (→ Catálogo)
- `urgencia`: `urgente | media | leve`
- `detalle` (texto libre, opcional)
- El **badge del centro** es derivado: máximo de las urgencias de sus
  necesidades (`Urgente`/`Atención media`/`Atención baja`/`Sin reporte`). No se
  almacena; se calcula al leer (ADR 0005).

**Categoría de catálogo** (administrable por el moderador; ADR 0006)
- `id`, `nombre`, `es_insumo` (bool: bien vs no-bien), `activa`

**Código de gestión** (ADR 0002)
- `id`, `centro_id`, `valor` (opaco, aleatorio; guardar **hash**, no el texto)
- `rol`: `responsable | voluntario`
- `etiqueta` (autodeclarada, libre), `creado_por` (código padre, nulo si raíz)
- `revocado_en` (nulo si activo)

**Movimiento** (inventario; ADR 0007) — solo sobre categorías con `es_insumo`
- `id`, `centro_id`, `tipo`: `entrada | salida`
- `categoria_id`, `cantidad` (número, opcional), `unidad` (texto libre, opcional)
- `contraparte` (texto libre: nombre del donante o del ente del Estado, opcional)
- `nota` (opcional)
- `registrado_por` (código de gestión → etiqueta), `registrado_en` (timestamp)

**Moderador**
- `id`, `nombre`, credencial real (gestión de cuentas fuera del modelo de código)

**Contacto de emergencia** (deseable; ADR de alcance en `CONTEXT.md`)
- `id`, `nombre`, `tipo`, `zona`, `telefonos[]`, `whatsapp_url` (opcional)

## 4. Endpoints (contrato funcional, agnóstico de tecnología)

Nombres ilustrativos; el equipo define rutas y verbos exactos.

**Directorio público (sin auth)**
- Listar/buscar centros con filtros `texto`, `estado`, `municipio`, `categoria`,
  `urgencia`. Devuelve solo centros no ocultos. Optimizado y cacheable.
- Ver ficha de un centro.
- Obtener el **reporte** en texto plano de un centro (puede resolverse en cliente
  a partir de la ficha ya cargada; ver §5).
- Reportar un centro (denuncia abierta a cualquiera → cola de moderación).
- Listar contactos de emergencia *(deseable)*.

**Alta de centro (sin auth, baja fricción)**
- Crear centro: formulario corto → crea el centro `sin_verificar` y **devuelve el
  código raíz una sola vez**. Sin paso de login.

**Panel de gestión del centro (auth = código de gestión)**
- Canjear código → sesión del centro con su rol.
- Editar ficha (responsable): datos + lista de necesidades con urgencia/detalle.
- Registrar entrada / salida (responsable y voluntario).
- Listar movimientos del centro; corregir/anular: responsable cualquiera,
  voluntario solo los propios recientes (ADR 0002).
- Crear / revocar / etiquetar códigos de voluntario (solo responsable).
- Ver totales derivados del inventario (etiquetados "registrado", no existencia).

**Panel de moderación (auth = cuenta de moderador)**
- Cola de centros `sin_verificar` y de reportes; verificar / ocultar.
- **Crear centros (nacen `verificado`) y editar cualquier centro.**
- Fusionar centros duplicados.
- Reemitir/revocar código raíz de un centro (recuperación; ADR 0002).
- Gestionar el catálogo (alta/baja de categorías, marcar `es_insumo`).
- Gestionar contactos de emergencia *(deseable)*.
- Gestionar cuentas de moderador y ver métricas básicas.

## 5. El Reporte (texto plano compartible)

Función de primera necesidad (no adorno): un botón **"Copiar reporte"** por
centro que copia al portapapeles un resumen en texto plano, listo para pegar en
WhatsApp/SMS. **Debe resolverse en el cliente** a partir de la ficha ya cargada,
para funcionar sin red. Formato de referencia (de los ejemplos del proyecto):

```
CENTRO: <nombre>
Municipio: <municipio>
Dirección: <direccion>
Contacto: <contacto?>
Ubicación: <ubicacion_url?>
Vialidad: <vialidad?>
Verificado: <Sí|No>
NECESIDADES:
- [URGENTE|MEDIA|LEVE] <categoria>: <detalle?>
Actualizado: <fecha y hora>
```

## 6. Restricciones no funcionales (vinculantes; ADR 0003)

- **Red móvil degradada** como contexto base; móvil como dispositivo principal.
- **Directorio público** medido en Slow 4G / Android gama media-baja:
  primera carga **≤ ~170 KB** comprimida; **FCP ≤ ~1,8 s**; **LCP ≤ ~2,5 s**;
  **se lee y se busca aunque el JS no cargue o falle**; sin imágenes pesadas.
  (Números ajustables tras una prueba con contenido real.)
- **Usabilidad móvil** cuidada en los flujos de alta frecuencia (registrar
  entrada/salida en la puerta).
- Códigos de gestión: guardar **hash**, nunca el texto plano.

## 7. Alcance: mínimo vs deseable

**Mínimo para salir**
- Directorio público (buscar/filtrar, ficha, reporte copiable, reportar centro).
- Alta de centro con devolución del código raíz.
- Panel de gestión: editar ficha + necesidades; registrar y listar movimientos;
  crear/revocar códigos de voluntario; totales derivados.
- Panel de moderación: verificar/ocultar, fusionar duplicados, reemitir código
  raíz, gestionar catálogo, cuentas de moderador.

**Deseable**
- Señales del inventario que empujan a actualizar la ficha (ADR 0005).
- Contactos de emergencia en la home.
- PWA / funcionamiento offline del Directorio.
- Aviso de ficha desactualizada (frescura).
- Autoservicio de recuperación por OTP (ADR 0002).
