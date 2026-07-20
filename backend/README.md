# designfabric (backend)

Backend Python (FastAPI + jobs GPU/CPU) de DesignFabric: fusión del dominio
de ClearCut (eliminación de fondo, escalado/vectorizado) y de DesignFabric
(generación de stickers vía Ollama + FLUX.2 Klein).

Ver el `README.md` de la raíz del repo para la documentación completa del
proyecto. Este archivo existe únicamente para que `backend/` sea un paquete
Python autocontenido — puede copiarse y construirse (`uv sync`) de forma
independiente, sin depender de rutas fuera de esta carpeta (necesario para el
empaquetado de la app de escritorio, que copia `backend/` a `userData` en el
primer arranque).
