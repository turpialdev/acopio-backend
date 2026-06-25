# Acceso por código de gestión opaco, con roles y etiquetas autodeclaradas

El inventario es privado, así que el operador necesita identidad; pero el
requisito de fricción mínima en la "hora cero" descarta cuentas con contraseña y
OTP por correo/SMS (infraestructura frágil con la red caída). Adoptamos el
modelo del referente (`apoyo-venezuela.com/gestion`) y lo extendemos con roles.

Decisiones:

- **Código de gestión opaco y aleatorio.** El acceso a un centro es "quien tiene
  el código". El rol se guarda en el servidor; **no** se incrusta en el código
  (si fuera deducible de su forma, sería falsificable). Ventaja sobre un enlace:
  un código se puede dictar por voz o SMS.
- **Dos roles.** El *Responsable* (código raíz, generado al registrar el centro)
  edita la ficha pública, registra entradas/salidas, crea/revoca códigos de
  voluntario y corrige/elimina cualquier registro. El *Voluntario* (código
  creado por el responsable) registra entradas/salidas y consulta; puede
  corregir solo sus registros recientes; no edita la ficha, no crea códigos, no
  toca registros ajenos. Limitar lo destructivo al responsable acota el daño si
  un código de voluntario se filtra.
- **Trazabilidad por etiqueta autodeclarada.** Cada código lleva una etiqueta
  libre que pone su creador ("Juan – puerta"); cada registro del inventario
  queda estampado con el código que lo hizo. El responsable da su nombre y un
  teléfono opcional al registrar (un campo, baja fricción), que sirve también de
  contacto de recuperación.

## Consequences

- El código es un "token al portador": si se filtra, queda expuesto. Mitigación:
  el responsable revoca códigos de voluntario; el moderador revoca/reemite el del
  responsable. El contenido es operativo, no financiero, así que el nivel de
  riesgo es aceptable.
- La trazabilidad apunta a una etiqueta en la que confía el responsable, no a una
  identidad verificada. Verificar identidad de verdad costaría más de lo que vale
  en este dominio.
- Perder el código raíz sin teléfono de recuperación deja al centro sin acceso
  hasta que intervenga un moderador.
