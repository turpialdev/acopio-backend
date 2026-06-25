# Sistema único e independiente: directorio + inventario sobre una entidad central

Existe ya un directorio público funcional (`apoyo-venezuela.com`) que cubre el
primer entregable. Aun así construimos un sistema propio e independiente porque
el valor diferencial está en el **inventario** (entradas de donantes / salidas a
entes del Estado), algo que el referente no ofrece, y queremos no depender de
terceros para el directorio.

Decidimos un **sistema único integrado** (opción A) en lugar de dos aplicaciones
separadas (opción B), con el **Centro de acopio como entidad central**: cada
centro se registra una vez y desde ahí gestiona tanto su ficha pública en el
Directorio como su Inventario privado. El Directorio público es en buena medida
una proyección de lo que los centros mantienen.

## Considered Options

- **(A) Sistema único, entidad "Centro de acopio".** Elegida. Permite que el
  inventario alimente la necesidad pública (si se agota el agua, la ficha sube a
  "Urgente" casi sin trabajo manual), una sola fuente de verdad y un solo login
  por centro. Es justamente la sinergia que un directorio-solo no puede dar.
- **(B) Dos apps separadas** vinculadas por un id de centro. Descartada: pierde
  la sinergia directorio↔inventario, que es la razón de construir propio.
- **No construir; contribuir al referente.** Descartada por la decisión de
  independencia operativa, pero sigue siendo la vía de mayor impacto si el único
  objetivo fuera el directorio.

## Consequences

- Acopla la autenticación al sistema desde temprano: para llegar a su inventario
  privado, el operador del centro necesita alguna forma de identidad. Esto añade
  fricción en la "hora cero", en tensión directa con el requisito de mantener la
  fricción de registro al mínimo. La forma de identidad se decide aparte.
- Como el directorio es un respaldo y no aspira a ser el directorio canónico del
  país, puede ser más liviano que el referente e incluso arrancar sembrado con
  datos públicos; el esfuerzo de ingeniería se concentra en el inventario.
