# image-conversion-batch

## Purpose

Convertir un lote de imágenes de formatos mixtos (JPEG/JPG/PNG/WEBP) a un único formato destino y empaquetar el resultado en un `.zip` descargable, con reporte por ítem y resiliencia a fallos parciales. Vive como el modo Lote del tab "Conversión de imágenes" dentro de la sección "Utilidades".

## Requirements

### Requirement: Convertir un lote de imágenes a un único formato destino

El sistema SHALL permitir seleccionar múltiples imágenes de formatos mixtos (JPEG/JPG/PNG/WEBP) y convertirlas **todas al mismo formato destino** elegido, en un único job asíncrono con afinidad de CPU que reporta progreso al frontend. Cada imagen del lote SHALL conservar su nombre base original con la extensión del formato destino.

#### Scenario: Lote de formatos mixtos a WEBP

- **WHEN** el usuario selecciona un PNG, un JPEG y un WEBP, elige destino `WEBP` y ejecuta la conversión en lote
- **THEN** el sistema convierte las tres imágenes a WEBP conservando cada nombre base con extensión `.webp`

#### Scenario: Reglas de calidad y transparencia por ítem

- **WHEN** un lote con destino `JPEG` incluye imágenes con transparencia
- **THEN** cada imagen con alpha se aplana sobre blanco y el nivel de calidad seleccionado se aplica a cada archivo, igual que en la conversión individual

### Requirement: Empaquetado del lote en un archivo ZIP

Al completar una conversión en lote, el sistema SHALL empaquetar todas las imágenes convertidas en un único archivo `.zip` en el directorio de salida y exponer su `zip_url` vía el mount `/output` para su descarga. El sistema SHALL evitar colisiones de nombres dentro del ZIP cuando dos entradas produzcan el mismo nombre de archivo.

#### Scenario: Descarga del ZIP resultante

- **WHEN** la conversión en lote termina correctamente
- **THEN** el sistema devuelve una `zip_url` que apunta a un `.zip` conteniendo todas las imágenes convertidas

#### Scenario: Nombres duplicados en el lote

- **WHEN** dos imágenes de entrada de carpetas distintas comparten el mismo nombre base y se convierten al mismo formato
- **THEN** el sistema asegura nombres únicos dentro del ZIP para no sobrescribir ninguna de las dos salidas

### Requirement: Reporte de resultados por ítem y continuación ante fallos

El sistema SHALL reportar, al terminar el lote, cuántas imágenes se esperaban y cuántas se produjeron, junto con el estado por ítem. Si una imagen individual falla al convertirse, el sistema SHALL registrar ese fallo y continuar con el resto del lote en vez de abortar todo el job.

#### Scenario: Un ítem falla y el resto continúa

- **WHEN** durante un lote una imagen está corrupta y no puede decodificarse
- **THEN** el sistema marca ese ítem como fallido con su mensaje de error, produce el ZIP con las imágenes restantes convertidas, y reporta el conteo esperado vs. producido
