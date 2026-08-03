# image-conversion

## Purpose

Convertir una imagen individual entre los formatos soportados (JPEG/JPG/PNG/WEBP) usando Pillow como motor, con control de calidad y aplanado de transparencia sobre blanco al exportar a JPEG. Vive como tab "Conversión de imágenes" (modo Individual) dentro de la sección "Utilidades".

## Requirements

### Requirement: Convertir una imagen individual entre formatos soportados

El sistema SHALL permitir convertir una imagen de entrada a uno de los formatos soportados —**JPEG, JPG, PNG, WEBP**— usando Pillow como motor. La conversión SHALL ejecutarse como job asíncrono con afinidad de CPU y reportar progreso al frontend. El formato de entrada SHALL detectarse por contenido/extensión del archivo, no depender de que coincida con el destino.

#### Scenario: Conversión PNG a WEBP exitosa

- **WHEN** el usuario selecciona una imagen PNG, elige el formato destino `WEBP` y ejecuta la conversión
- **THEN** el sistema produce un archivo `.webp` en el directorio de salida y devuelve una `image_url` servida por el mount `/output`

#### Scenario: Formato destino igual al de origen

- **WHEN** el usuario convierte una imagen JPEG eligiendo destino `JPEG`
- **THEN** el sistema re-codifica la imagen y produce un `.jpg` válido sin error (por ejemplo para aplicar un nuevo nivel de calidad)

#### Scenario: JPG y JPEG comparten codec

- **WHEN** el usuario elige `JPG` como formato destino
- **THEN** el sistema usa el codec JPEG de Pillow y escribe el archivo con extensión `.jpg`

### Requirement: Aplanado de transparencia al convertir a JPEG

Cuando la imagen de origen tiene canal alpha (PNG/WEBP con transparencia) y el formato destino es JPEG/JPG, el sistema SHALL aplanar la imagen componiéndola **sobre un fondo blanco** antes de guardarla como RGB, dado que JPEG no soporta transparencia. Las imágenes sin canal alpha SHALL convertirse a JPEG sin alteración de fondo.

#### Scenario: PNG con transparencia a JPEG

- **WHEN** el usuario convierte un PNG con áreas transparentes a `JPEG`
- **THEN** las áreas transparentes aparecen en blanco en el archivo `.jpg` resultante y el archivo no contiene canal alpha

#### Scenario: Imagen opaca a JPEG

- **WHEN** el usuario convierte a `JPEG` una imagen que no tiene canal alpha
- **THEN** el sistema la guarda como JPEG sin introducir ningún relleno de fondo

### Requirement: Control de calidad de compresión

El sistema SHALL exponer un control de **calidad 0–100** aplicado al guardar en JPEG/JPG y WEBP, y SHALL ofrecer una opción de **WEBP sin pérdida (lossless)**. Para PNG el sistema SHALL guardar con optimización activada. Si el usuario no especifica calidad, el sistema SHALL usar un valor por defecto de **90**.

#### Scenario: Calidad aplicada a JPEG

- **WHEN** el usuario fija la calidad en 60 y convierte a `JPEG`
- **THEN** el archivo resultante se codifica con ese nivel de calidad (menor peso que a calidad 90 para la misma imagen)

#### Scenario: WEBP lossless ignora el slider de calidad

- **WHEN** el usuario activa WEBP lossless y convierte a `WEBP`
- **THEN** el sistema guarda en modo sin pérdida independientemente del valor del slider de calidad

#### Scenario: Calidad no aplica a PNG

- **WHEN** el usuario convierte a `PNG`
- **THEN** el sistema guarda el PNG optimizado y el control de calidad no afecta la salida

### Requirement: Entrega y exportación del archivo convertido

Tras una conversión individual exitosa, el sistema SHALL escribir la salida en el directorio de salida configurado, exponer su `image_url` vía el mount `/output` para previsualizarla, y permitir al usuario **exportar el archivo** a una ubicación elegida mediante el diálogo nativo de guardado, siguiendo el patrón de la herramienta de escalado (`exportImage`).

#### Scenario: Exportar el resultado

- **WHEN** la conversión individual termina y el usuario pulsa "Exportar"
- **THEN** el sistema abre un diálogo nativo de guardado con un nombre por defecto derivado del archivo original y su nueva extensión, y escribe el archivo convertido en la ruta elegida
