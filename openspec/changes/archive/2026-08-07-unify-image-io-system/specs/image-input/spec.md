## Purpose

Define cómo una pantalla adquiere su imagen de entrada desde múltiples orígenes (diálogo nativo,
portapapeles y arrastrar-y-soltar), con validación de formato y un ciclo de vida acotado del archivo
temporal, para que el backend siempre reciba una ruta de archivo válida sin fugas de temporales.

## ADDED Requirements

### Requirement: Selección de imagen por diálogo nativo

La zona de entrada de imagen SHALL permitir elegir un archivo mediante el diálogo nativo del sistema,
y al confirmarse SHALL exponer la ruta del archivo y una previsualización de la imagen.

#### Scenario: El usuario elige una imagen con el diálogo

- **WHEN** el usuario abre el diálogo nativo y selecciona un archivo de imagen soportado
- **THEN** la zona de entrada muestra su previsualización y la ruta queda disponible como entrada para procesar

#### Scenario: El usuario cancela el diálogo

- **WHEN** el usuario abre el diálogo nativo y lo cancela sin elegir archivo
- **THEN** la entrada actual no cambia y no se produce ningún error

### Requirement: Pegar imagen desde el portapapeles

La zona de entrada de imagen SHALL aceptar una imagen pegada desde el portapapeles (Ctrl+V) cuando la
zona tiene el foco o está activa, materializando los bytes del portapapeles en un archivo temporal en
disco cuya ruta se usa como entrada.

#### Scenario: Pegar una imagen válida

- **WHEN** el usuario pega (Ctrl+V) una imagen soportada (PNG, JPEG o WEBP) sobre la zona de entrada
- **THEN** el sistema escribe los bytes en un archivo temporal, muestra su previsualización y usa esa ruta como entrada

#### Scenario: Pegar contenido que no es una imagen

- **WHEN** el usuario pega contenido que no es una imagen soportada (texto, HTML u otro formato)
- **THEN** no se crea ningún archivo temporal, la entrada actual no cambia y no se interrumpe al usuario

### Requirement: Soltar imagen con arrastrar-y-soltar

La zona de entrada de imagen SHALL aceptar una imagen soltada mediante arrastrar-y-soltar, usando el
mismo mecanismo de archivo temporal y la misma validación que el pegado desde el portapapeles.

#### Scenario: Soltar una imagen válida

- **WHEN** el usuario arrastra y suelta un archivo de imagen soportado sobre la zona de entrada
- **THEN** el sistema materializa la imagen en un archivo temporal, muestra su previsualización y usa esa ruta como entrada

#### Scenario: Soltar contenido que no es una imagen

- **WHEN** el usuario suelta un archivo o contenido que no es una imagen soportada
- **THEN** no se crea ningún archivo temporal y la entrada actual no cambia

### Requirement: Un único archivo temporal por input

Cada zona de entrada SHALL mantener como máximo un archivo temporal a la vez. Cuando se pega o se
suelta una imagen nueva, el archivo temporal anterior de esa zona (si lo hubiera) SHALL eliminarse
antes o al momento de registrar el nuevo.

#### Scenario: Reemplazar una imagen pegada por otra

- **WHEN** una zona de entrada ya tiene un archivo temporal por un pegado previo y el usuario pega otra imagen
- **THEN** el archivo temporal anterior se elimina del disco y solo queda el archivo temporal de la imagen más reciente

#### Scenario: Elegir por diálogo tras haber pegado

- **WHEN** una zona de entrada tiene un archivo temporal por pegado y el usuario elige después una imagen por el diálogo nativo
- **THEN** el archivo temporal previo se elimina, ya que la nueva entrada proviene de una ruta real en disco

### Requirement: Limpieza de temporales al cerrar la app

Todos los archivos temporales creados por pegado o arrastrar-y-soltar SHALL eliminarse cuando la
aplicación se cierra, de modo que no se acumulen entre sesiones.

#### Scenario: Cierre de la aplicación

- **WHEN** la aplicación se cierra habiendo creado uno o más archivos temporales de imágenes
- **THEN** todos esos archivos temporales se eliminan del disco durante el cierre
