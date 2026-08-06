# halftone-conversion

## Purpose

Convertir una imagen individual a su versión con semitonos (halftone) usando el core extraído del Space `halftone-converter` (PIL + numpy), replicando 1:1 las opciones del Gradio original. Produce un PNG RGBA transparente a resolución fija (4500×5400 @300) apto para print-on-demand / serigrafía. Vive como tab "Semitonos" (sección "Retocar") y se ejecuta como job asíncrono con afinidad de CPU.

## Requirements

### Requirement: Convertir una imagen individual a su versión con semitonos

El sistema SHALL permitir convertir una imagen de entrada a una versión con semitonos (halftone) usando el core extraído del Space `halftone-converter` (PIL + numpy), produciendo la salida **pixel-idéntica** al algoritmo original. La conversión SHALL ejecutarse como job asíncrono con **afinidad de CPU** y reportar progreso al frontend. La imagen de entrada SHALL provenir de un upload manual del usuario.

#### Scenario: Conversión halftone exitosa

- **WHEN** el usuario sube una imagen, ajusta los parámetros y ejecuta el export
- **THEN** el sistema encola un job CPU, produce un archivo en el directorio de salida y devuelve una `image_url` servida por el mount `/output`

#### Scenario: Sin imagen de entrada

- **WHEN** el usuario intenta ejecutar el export sin haber subido una imagen
- **THEN** el sistema no encola ningún job y la UI indica que falta la imagen de entrada

### Requirement: Salida PNG RGBA transparente conservando color

El resultado SHALL ser un **PNG RGBA** en el que el patrón de semitonos vive en el **canal alpha** y los colores originales de la imagen se conservan en los canales RGB. La resolución de salida y el DPI SHALL estar **fijos en 4500×5400 @300** (redimensionando preservando aspecto, sin ampliar más allá de esa caja), replicando el comportamiento hardcodeado del Gradio original; no se exponen como controles.

#### Scenario: Formato y transparencia de salida

- **WHEN** se completa una conversión halftone
- **THEN** el archivo resultante es un `.png` con canal alpha, donde las zonas sin punto quedan transparentes y las zonas con punto conservan el color original

#### Scenario: Resolución fija con aspecto preservado

- **WHEN** se procesa una imagen de aspecto arbitrario
- **THEN** el sistema la ajusta dentro de la caja de 4500×5400 preservando la relación de aspecto y marca el DPI del archivo en 300

### Requirement: Opciones de crop de fondo negro

El sistema SHALL exponer una opción **Crop Black Background** (checkbox, default activado) que recorta bordes casi-negros alrededor de la imagen, y un **Crop Threshold** (0–255, paso 1, default 25): los píxeles cuyos canales RGB están todos por debajo del umbral se tratan como fondo negro. Cuando el crop está desactivado, la imagen SHALL procesarse sin recorte.

#### Scenario: Crop activado recorta bordes negros

- **WHEN** el crop está activado y la imagen tiene un borde negro alrededor del diseño
- **THEN** el sistema recorta ese borde antes de generar el halftone

#### Scenario: Crop desactivado

- **WHEN** el usuario desactiva Crop Black Background
- **THEN** el sistema no recorta ningún borde y procesa la imagen completa

### Requirement: Ajuste de niveles (tone curve)

El sistema SHALL exponer un ajuste de niveles estilo Photoshop con tres controles: **Black Point** (0–255, paso 1, default 16), **White Point** (0–255, paso 1, default 100) y **Gamma** (0.1–3.0, paso 0.1, default 1.0), aplicados sobre la versión en escala de grises antes de generar el halftone.

#### Scenario: Aplicación de niveles

- **WHEN** el usuario sube el Black Point y baja el White Point
- **THEN** las sombras por debajo del black point se vuelven negro puro y los brillos por encima del white point se vuelven blanco puro en la escala de grises intermedia

### Requirement: Inversión para prenda oscura

El sistema SHALL exponer un checkbox **Invert for Dark Garment** (default desactivado) que invierte los valores tonales para imprimir correctamente sobre tela oscura.

#### Scenario: Inversión activada

- **WHEN** el usuario activa Invert for Dark Garment
- **THEN** los valores tonales se invierten antes de generar el patrón de semitonos

### Requirement: Método de semitonos

El sistema SHALL permitir elegir entre dos métodos: **`halftone`** (trama de puntos clásica, default) y **`diffusion`** (difusión de error Floyd–Steinberg). Los controles de trama (frecuencia, ángulo, forma) SHALL aplicar únicamente al método `halftone` y SHALL ignorarse cuando el método es `diffusion`.

#### Scenario: Método halftone usa trama de puntos

- **WHEN** el método seleccionado es `halftone`
- **THEN** el sistema genera el patrón con la frecuencia, ángulo y forma configurados

#### Scenario: Método diffusion ignora parámetros de trama

- **WHEN** el método seleccionado es `diffusion`
- **THEN** el sistema aplica Floyd–Steinberg y los parámetros de frecuencia, ángulo y forma no afectan el resultado

### Requirement: Parámetros de trama (frecuencia, ángulo, forma)

Para el método `halftone`, el sistema SHALL exponer: **Screen Frequency (LPI)** (5–100, paso 1, default 35), **Screen Angle** (0–90°, paso 0.5, default 23.5) y **Dot Shape** (`round` default, o `line`). El tamaño del punto SHALL derivarse de la frecuencia relativa al DPI de salida.

#### Scenario: Frecuencia controla densidad del punto

- **WHEN** el usuario baja la frecuencia LPI
- **THEN** los puntos del halftone se vuelven más grandes y visibles

#### Scenario: Forma de línea

- **WHEN** el usuario selecciona Dot Shape `line`
- **THEN** el sistema produce tramado de líneas paralelas en lugar de puntos circulares
