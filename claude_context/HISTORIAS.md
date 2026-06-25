# Historias de usuario — Acopio Venezuela

Cada historia lleva una etiqueta de alcance: **[Mínimo]** (necesario para salir) o
**[Deseable]** (valor añadido que no bloquea la salida), según ADR 0005. El
vocabulario es el de `CONTEXT.md`.

Formato: _Como <rol>, quiero <objetivo>, para <beneficio>._ Las historias con
reglas no obvias incluyen criterios de aceptación.

---

## Público (donante / ciudadano)

**P1 — [Mínimo]** Como donante, quiero buscar y filtrar centros por texto, estado,
municipio, categoría de necesidad y urgencia, para encontrar a dónde llevar lo que
tengo.
- El Directorio no muestra centros ocultos.
- El filtro funciona sobre categorías del catálogo (no texto libre).
- La lista se ve y se puede buscar aunque el JS no haya cargado (ADR 0003).

**P2 — [Mínimo]** Como donante, quiero ver la ficha de un centro (dirección,
contacto, ubicación, vialidad, verificación, necesidades con urgencia y detalle, y
cuándo se actualizó), para decidir si voy y qué llevo.
- La fecha de **actualización** es visible y prominente: el donante debe poder
  juzgar si "Urgente: agua" es de hace 20 minutos o de hace dos días.
- El badge de urgencia del centro es el máximo de sus necesidades.

**P3 — [Mínimo]** Como donante, quiero copiar el reporte de un centro en texto
plano con un toque, para reenviarlo por WhatsApp/SMS a quien no puede abrir el
sitio.
- Copiar funciona **sin red** una vez cargada la página.
- Donde el navegador lo permita, además compartir nativo; si no, cae a copiar.

**P4 — [Mínimo]** Como ciudadano, quiero reportar un centro falso, duplicado o
peligroso, para que la moderación lo revise.
- El reporte entra a una cola de moderación; no oculta el centro automáticamente.

**P5 — [Deseable]** Como ciudadano en pánico tras una réplica, quiero ver los
contactos de emergencia (bomberos, hospitales, protección civil) con botón de
llamar, para pedir ayuda sin salir del sitio.

**P6 — [Deseable]** Como donante con conexión intermitente, quiero que el
Directorio funcione offline (PWA), para consultarlo durante un corte.

---

## Responsable de centro

**R1 — [Mínimo]** Como responsable, quiero registrar mi centro con un formulario
corto (imitando `apoyo-venezuela.com/centros/nuevo`) y recibir mi código raíz en
pantalla, para empezar a gestionarlo sin crear cuenta ni contraseña.
- Campos de **ubicación/centro**: estado (selector), municipio (depende del
  estado), nombre del centro, dirección, link de Maps (opcional), contacto público
  (opcional), estado de vialidad (opcional).
- Campos del **responsable** (uso interno, **no** se muestran en el Directorio):
  nombre, teléfono (sirve de contacto de recuperación) y **cargo**
  (Propietario / Socio / Director / Gerente).
- Sin paso de login. El centro nace `sin_verificar` pero **visible** (ADR 0004).
- El código se muestra **una sola vez**, con aviso claro de guardarlo.

**R2 — [Mínimo]** Como responsable, quiero entrar a mi panel pegando o dictándome
el código de gestión, para gestionar el centro desde cualquier teléfono.

**R3 — [Mínimo]** Como responsable, quiero editar la ficha pública y la lista de
necesidades (categoría del catálogo + urgencia + detalle libre), para que los
donantes sepan exactamente qué hace falta y con qué prioridad.
- Al guardar, `actualizado_en` se refresca.

**R4 — [Mínimo]** Como responsable, quiero registrar entradas (de donantes) y
salidas (a entes del Estado) con cantidad opcional, para llevar el libro del
centro sin fricción.

**R5 — [Mínimo]** Como responsable, quiero ver el libro de movimientos y corregir o
anular cualquier registro, para arreglar errores de cualquiera del equipo.

**R6 — [Mínimo]** Como responsable, quiero crear códigos de voluntario con una
etiqueta ("Juan – puerta") y revocarlos, para sumar manos y cortar el acceso de un
código filtrado.
- Los códigos son opacos; el rol vive en el servidor (ADR 0002).

**R7 — [Mínimo]** Como responsable que perdió su código raíz, quiero pedir al
moderador que me reemita uno nuevo, para recuperar el acceso.
- Verificación con el teléfono de recuperación si lo hay; si no, re-registro +
  fusión de duplicado (ADR 0002). Mediado por moderador, no instantáneo.

**R8 — [Deseable]** Como responsable, quiero que el sistema me avise cuando el
inventario sugiere actualizar la ficha ("hoy salió más agua de la que entró"),
para mantener la necesidad pública al día. El sistema sugiere; yo publico (ADR 0005).

---

## Voluntario

**V1 — [Mínimo]** Como voluntario, quiero entrar con el código que me dio el
responsable, para ayudar a registrar movimientos.

**V2 — [Mínimo]** Como voluntario en la puerta, quiero registrar entradas y salidas
rápido y con pocos toques, para no frenar la fila de donantes.
- Flujo de alta frecuencia: máxima usabilidad móvil (ADR 0003).
- Cada movimiento queda estampado con mi código/etiqueta.

**V3 — [Mínimo]** Como voluntario, quiero corregir un error reciente **mío**, para
arreglar una errata sin buscar al responsable.
- Solo registros propios y recientes; no ajenos, no la ficha, no códigos (ADR 0002).

**V4 — [Mínimo]** Como voluntario, quiero consultar el libro de movimientos del
centro, para ver qué se ha recibido y entregado.

---

## Moderador

**M1 — [Mínimo]** Como moderador, quiero una cola de centros `sin_verificar` y de
reportes, para curar el Directorio de forma reactiva (ADR 0004).
- Priorizable por urgencia y tráfico.

**M2 — [Mínimo]** Como moderador, quiero verificar u ocultar un centro, para dar el
sello de confianza o retirar lo falso/peligroso.

**M3 — [Mínimo]** Como moderador, quiero fusionar centros duplicados, porque varias
personas registran el mismo lugar (ADR 0004).

**M4 — [Mínimo]** Como moderador, quiero reemitir o revocar el código raíz de un
centro, para resolver recuperaciones y códigos filtrados (ADR 0002).

**M5 — [Mínimo]** Como moderador, quiero gestionar el catálogo de categorías
(alta/baja, marcar si es insumo o no-bien), para mantener el filtro coherente sin
un despliegue (ADR 0006).

**M6 — [Mínimo]** Como moderador, quiero gestionar cuentas de moderador, para que el
equipo opere la solución.

**M7 — [Mínimo]** Como moderador, quiero crear centros (que nacen **verificados**
por defecto) y editar cualquier centro, para sembrar el Directorio con datos
públicos o de confianza y corregir fichas cuando haga falta.
- Un centro creado por un moderador no pasa por la cola de verificación.
- La edición del moderador alcanza cualquier campo de la ficha, no solo el
  estado de verificación.

**M8 — [Deseable]** Como moderador, quiero ver métricas básicas (centros por
estado, urgentes activos, movimientos por día), para entender la operación.

**M9 — [Deseable]** Como moderador, quiero gestionar los contactos de emergencia de
la home, para mantenerlos frescos (un teléfono muerto cuesta minutos valiosos).
