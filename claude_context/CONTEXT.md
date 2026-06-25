# Acopio Venezuela

Sistema web para coordinar ayuda humanitaria tras el terremoto del 24/06/2026:
un directorio público de centros de acopio y un gestor de inventario para cada
centro. Sistema independiente; el inventario es el núcleo de valor y el
directorio existe para no depender de terceros.

## Lenguaje

**Centro de acopio**:
Lugar físico que recibe donaciones e insumos. Es la entidad central del
sistema: cada centro gestiona su ficha pública en el Directorio y su Inventario
privado.
_Evitar_: punto de recolección, sede, local.

**Directorio**:
Vista pública y de solo lectura de los centros de acopio y lo que necesitan.
Cualquier persona lo consulta sin cuenta. Es, en gran medida, una proyección de
los datos que cada centro mantiene.
_Evitar_: listado, mapa.

**Inventario**:
Registro privado de cada centro de lo que entra (de donantes) y lo que sale
(hacia entes del Estado). Solo visible para el operador del centro.
_Evitar_: stock, almacén, bodega.

**Insumo**:
Tipo de bien que un centro necesita, recibe o entrega (p. ej. agua potable,
alimentos no perecederos, medicamentos básicos, insumos médicos). Puede llevar
un detalle en texto libre.
_Evitar_: artículo, producto, ítem, suministro.

**Donante**:
Persona u organización que lleva insumos a un centro. Origen de una entrada.
_Evitar_: contribuyente, aportante.

**Ente del Estado**:
Organismo gubernamental que retira insumos de un centro para distribuirlos.
Destino de una salida.
_Evitar_: autoridad, gobierno, institución.

## Acceso

**Código de gestión**:
Cadena opaca y aleatoria que da acceso a gestionar un centro. El rol que otorga
vive en el servidor, no dentro del código. Se puede dictar por voz o SMS. Lleva
una etiqueta libre y autodeclarada (no verificada) que su creador le asigna.
_Evitar_: contraseña, token, clave.

**Responsable de centro**:
Persona que posee el código raíz de un centro, generado al registrarlo. Edita
la ficha pública, registra entradas y salidas, crea y revoca códigos de
voluntario, y corrige o elimina cualquier registro del inventario.
_Evitar_: dueño, admin, encargado.

**Voluntario**:
Persona con un código creado por el Responsable. Registra entradas y salidas y
consulta el inventario; puede corregir sus propios registros recientes, pero no
edita la ficha pública, no crea códigos ni toca registros ajenos.
_Evitar_: colaborador, ayudante, usuario.

**Moderador**:
Persona del equipo que opera la solución. Cuenta real (no código). Cura la
calidad del Directorio (aprobar/verificar, ocultar, fusionar duplicados) y
administra la plataforma (recuperar códigos raíz, catálogo de insumos, cuentas
de moderador, métricas).
_Evitar_: administrador, operador, staff.
