# Inventario como libro de movimientos, no como saldo de existencias

El Inventario registra **movimientos** (entradas de donantes, salidas a entes del
Estado) como eventos con fecha/hora, insumo, cantidad opcional, código que los
registró y nota libre. **No** mantiene un saldo de existencias por insumo. Los
totales (sumas de entradas/salidas) se muestran como conveniencia derivada y
etiquetada ("registrado hoy: +200 / −150 agua"), nunca como existencia real.

Motivo (coherente con ADR 0005): el inventario de un acopio en el caos es
aproximado. Un saldo "exacto" pero falso es peor que ningún saldo, porque la
gente confía en él. El libro de movimientos es honesto ("esto es lo que
alcanzamos a anotar") y de menor fricción en la puerta: se anota lo que pasa
cuando pasa, sin cuadrar saldos ni cargar un inventario inicial.

## Consequences

- Las señales de la función deseable "asistido por inventario" ("hoy salió más
  agua de la que entró") salen del libro de movimientos sin necesidad de un saldo
  confiable.
- La cantidad es opcional (número + unidad libre, o nada): obligar a pesar y
  contar con precisión en la puerta es irreal.
- Si en el futuro un ente exige rendición de cuentas formal con existencias, será
  una capa nueva sobre el libro, no un cambio del modelo base.
