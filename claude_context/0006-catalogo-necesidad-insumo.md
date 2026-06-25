# Catálogo controlado de necesidades; insumo (bien) es el subconjunto que el inventario mueve

Las necesidades de un centro salen de un **catálogo controlado** que gestiona el
Moderador, con un **detalle en texto libre** opcional por necesidad. El catálogo
existe para que el filtro del Directorio funcione: texto libre puro fragmentaría
las categorías ("agua" / "Agua potable" / "agua embotellada") y mataría el filtro
y la agregación.

Se separan dos conceptos que el referente trata como uno solo:

- **Necesidad**: cualquier categoría del catálogo. La mayoría son bienes, pero
  algunas son **no-bienes** (p. ej. "voluntarios de rescate", transporte). La
  ficha pública lista necesidades.
- **Insumo**: la necesidad que **es un bien**. Es el único tipo que el Inventario
  puede mover (entradas y salidas). Un no-bien no tiene inventario.

## Por qué la distinción

El referente mete "Voluntarios de rescate" en la misma lista que "Agua potable".
Para el Directorio eso da igual. Pero el segundo entregable —el inventario— mueve
bienes: registrar una "entrada de voluntarios" no tiene sentido. Marcar desde el
modelo qué necesidades son insumos evita que el inventario tenga que filtrar
casos sin sentido más tarde.

## Consequences

- El catálogo es dato administrable, no código: el Moderador puede añadir
  categorías (y marcar si son insumo o no-bien) sin un despliegue.
- La ficha y el inventario comparten el catálogo, pero el inventario solo opera
  sobre las entradas marcadas como insumo.
