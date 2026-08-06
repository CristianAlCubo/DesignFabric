## ADDED Requirements

### Requirement: Previsualización rápida a resolución reducida

El sistema SHALL exponer una previsualización que genera el halftone a **resolución reducida** para permitir iterar sobre los parámetros sin pagar el costo del render a resolución completa. La preview SHALL aceptar los mismos parámetros que el export y SHALL reflejar los cambios de los controles.

#### Scenario: Preview refleja los parámetros actuales

- **WHEN** el usuario ajusta un control (por ejemplo el Black Point) con una imagen cargada
- **THEN** el sistema regenera la preview a baja resolución mostrando el efecto de ese parámetro

#### Scenario: Preview antes del export

- **WHEN** el usuario está ajustando parámetros y aún no ha exportado
- **THEN** el sistema muestra la preview sin producir el archivo full-res definitivo

### Requirement: LPI escalado proporcionalmente en la preview

Dado que el tamaño del punto depende de la resolución (`px_per_cycle = dpi / frequency`), la preview SHALL escalar la frecuencia LPI **proporcionalmente** a la razón entre la resolución de preview y la resolución de export, de modo que el patrón visto en la preview sea **representativo** del resultado final y no aparezca desproporcionadamente grueso.

#### Scenario: El punto de la preview es representativo del export

- **WHEN** se genera una preview a una fracción de la resolución full-res para el método `halftone`
- **THEN** el LPI efectivo de la preview se ajusta por esa misma fracción, de modo que el grosor relativo del punto coincide aproximadamente con el del export a resolución completa

#### Scenario: Aviso de fidelidad del resultado final

- **WHEN** el usuario visualiza la preview
- **THEN** la UI indica que el export a resolución completa es el render definitivo y que el método `diffusion` puede diferir levemente respecto de la preview
