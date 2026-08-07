# image-transfer

## Purpose

Permite que el resultado producido por una pantalla se envíe como imagen de entrada de otra pestaña,
de forma genérica entre cualquier par origen→destino, sin acoplar el mecanismo a un par fijo de
pantallas.

## Requirements

### Requirement: Enviar el resultado a otra pestaña

Una pantalla con un resultado de imagen SHALL poder enviar ese resultado como entrada de otra pestaña
compatible. Al hacerlo, el sistema SHALL navegar a la pestaña destino y precargar allí la imagen como
entrada, usando la ruta del resultado.

#### Scenario: Enviar un resultado a otra pantalla

- **WHEN** el usuario, con un resultado disponible, elige enviarlo a otra pestaña
- **THEN** la aplicación cambia a esa pestaña y su zona de entrada queda precargada con la imagen del resultado, lista para procesar

#### Scenario: No hay resultado que enviar

- **WHEN** el usuario intenta enviar a otra pestaña sin que exista un resultado disponible
- **THEN** no ocurre ninguna navegación ni transferencia

### Requirement: Menú contextual "Enviar a…" sobre el resultado

Al hacer click derecho sobre una vista de resultado de imagen que tiene un resultado disponible y
declara pantallas destino, el sistema SHALL abrir un menú contextual con una opción «Enviar a:» que
despliega un submenú anidado con las pantallas destino soportadas. Elegir una pantalla SHALL enviar el
resultado a esa pestaña (misma acción que la transferencia genérica). Cada vista de resultado SHALL
determinar por configuración qué pantallas destino ofrece; no existe una lista global fija.

#### Scenario: Enviar mediante el menú contextual

- **WHEN** el usuario hace click derecho sobre un resultado que declara una o más pantallas destino y elige una en el submenú «Enviar a:»
- **THEN** la aplicación navega a esa pestaña y precarga allí la imagen del resultado como entrada

#### Scenario: Resultado sin pantallas destino declaradas

- **WHEN** el usuario hace click derecho sobre un resultado que no declara ninguna pantalla destino
- **THEN** el menú contextual no ofrece la opción «Enviar a:» (o no se abre por esa causa)

#### Scenario: No hay resultado todavía

- **WHEN** el usuario hace click derecho sobre una vista de resultado que aún no tiene imagen
- **THEN** no se ofrece la acción de enviar

### Requirement: La transferencia no depende de un par fijo de pantallas

El mecanismo de envío entre pestañas SHALL ser genérico respecto de la pantalla origen y la de destino,
de modo que agregar una nueva pantalla que produzca o consuma imágenes no requiera modificar la lógica
de transferencia existente.

#### Scenario: Nueva pantalla como destino de transferencia

- **WHEN** se incorpora una pantalla que acepta imagen de entrada y se la designa como destino de una transferencia
- **THEN** puede recibir el resultado de cualquier pantalla origen sin cambios en el mecanismo de transferencia
