# Aplicación con backend de endpoints + front responsive; herramientas a cargo del equipo

El equipo es senior y competente en una arquitectura de backend (un servidor con
múltiples endpoints — no microservicios) y un front responsive. La elección de
lenguajes, frameworks y base de datos se delega al equipo. Lo que este documento
fija no son herramientas, sino la **forma funcional** y las **restricciones no
funcionales** que cualquier elección debe respetar.

Forma funcional:

- **Una sola aplicación desplegable**, no un conjunto de servicios separados. La
  escala lo justifica: cientos de centros como mucho, escrituras de inventario
  modestas. Separar en servicios solo añadiría superficie de fallo.
- **Directorio público**: lectura sin autenticación.
- **Panel de gestión del centro**: detrás del código de gestión (ver ADR 0002).
- **Panel de moderación/administración**: para el equipo que opera la solución.
- **Una sola base de datos** cubre centros, códigos, inventario y moderación.

Restricciones no funcionales (vinculantes, sea cual sea el stack):

- **Funciona en redes móviles degradadas.** Es el contexto real: gente en la
  calle, posibles cortes. El móvil es el dispositivo principal.
- **Directorio público ultraligero y de carga casi instantánea.** Payload
  inicial mínimo y muy cacheable. Esto descarta, de hecho, una SPA pesada que
  exija descargar megabytes de JS antes de ver el primer centro; cómo se logre
  (render en servidor, SPA con presupuesto de rendimiento estricto, etc.) lo
  decide el equipo, pero el resultado medible no es negociable.
- **Mejor usabilidad posible en móvil**, con especial cuidado en los flujos de
  alta frecuencia (registrar entradas/salidas en la puerta).

## Consequences

- El equipo tiene libertad de stack, pero queda atado a un presupuesto de
  rendimiento explícito para el directorio público. Conviene fijar una métrica
  concreta (p. ej. peso de la primera carga y tiempo a primer contenido en 3G)
  como criterio de aceptación.
