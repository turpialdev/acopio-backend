# Necesidad pública confirmada por humano; el inventario asiste, no decide

La "necesidad" que muestra el Directorio (urgencia + insumos requeridos) la
**declara y confirma el Responsable a mano**. El inventario, cuando se usa,
**sugiere** (señales como "hoy salió más agua de la que entró") y empuja a
actualizar la ficha, pero **nunca** publica nada por sí solo. Regla de oro: el
inventario sugiere, el humano publica.

Se descartó derivar la necesidad automáticamente del inventario: el inventario de
un acopio en el caos es aproximado e incompleto, y derivar señales públicas de
datos sucios transmitiría información falsa (anunciar "estamos bien de agua"
porque nadie registró las salidas). Además, "necesidad" es stock contra demanda
esperada, algo que juzga mejor la persona en la puerta que un umbral.

## Forma de la urgencia (corregido)

La urgencia es **por insumo requerido**: cada insumo de la lista lleva `Urgente`,
`Media` o `Leve`. El **badge del centro** (lo que se ve en la tarjeta) es
**derivado**, no se teclea aparte: toma el nivel más alto entre sus insumos —
`Urgente` si alguno es urgente, `Atención media` si el máximo es media,
`Atención baja` si solo hay leves, `Sin reporte` si no hay insumos. Así el
responsable marca urgencia donde toca y el badge se calcula solo; nunca mantiene
dos cosas en sync. Es "derivado", pero de un dato que el humano confirmó, así que
no rompe la regla de oro (el inventario sugiere, el humano publica).

Nota: una versión anterior de este ADR propuso una sola urgencia por centro para
ahorrar fricción. Se corrigió: con la lista de insumos ya presente, marcar el
nivel por línea es fricción marginal y el valor para el donante (saber qué es
desesperado vs qué hace media falta) es alto.

## Alcance: qué es mínimo y qué es deseable

Esta decisión parte las historias en dos niveles:

- **Mínimo para salir (a mano).** Directorio público + ficha editada a mano
  (urgencia e insumos) + gestión por código + moderación reactiva. Es, en
  esencia, igualar al referente más el modelo de código/roles.
- **Deseable (asistido por inventario).** Las señales del inventario que empujan
  a actualizar la ficha. Llega después del inventario mismo (segundo entregable)
  y nunca bloquea la salida del mínimo.

## Consequences

- El Directorio público funciona completo aunque ningún centro use el inventario.
  El inventario es valor añadido, no una dependencia del directorio.
- Las historias de usuario deben etiquetar explícitamente su nivel (mínimo vs
  deseable) para proteger la fecha de salida.
