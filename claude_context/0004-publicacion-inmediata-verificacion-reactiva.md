# Publicación inmediata con verificación reactiva

Un centro recién registrado **aparece en el Directorio de inmediato** con el
sello "sin verificar"; un moderador lo promueve a "verificado" después. La
moderación es reactiva (verificar y ocultar lo malo), no un portón que aprueba
todo antes de publicar.

Motivo: en un desastre, el costo de que un centro real quede invisible durante
horas supera al de exponer brevemente un centro sin verificar. La velocidad en la
"hora cero" pesa más que el filtrado previo.

## Dos ejes de estado, no uno

Para evitar sobrecargar la palabra "estado", el centro tiene dos dimensiones
independientes:

- **Estado de verificación** (lo controla el moderador): `sin verificar` →
  `verificado`, más `oculto` para spam/duplicados/peligrosos.
- **Estado de necesidad/urgencia** (lo refleja la ficha): `Urgente` /
  `Atención media` / `Sin reporte`. Cómo se fija se decide aparte (synergy
  directorio↔inventario).

## Consequences

- Un centro falso o duplicado es visible hasta que un moderador lo oculta.
  Mitigaciones: etiquetado "sin verificar" claro; botón de **reportar** abierto a
  cualquiera; los moderadores priorizan por urgencia y tráfico.
- La moderación necesita una cola de trabajo (centros sin verificar, reportes
  pendientes) en el panel, no un flujo de aprobación bloqueante.
- Duplicados son esperables (varias personas registran el mismo colegio); la
  fusión de duplicados es una función de moderación de primera necesidad.
