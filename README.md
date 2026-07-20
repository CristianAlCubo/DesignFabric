# DesignFabricV2

Fusión de **ClearCut** (eliminación de fondo de imágenes + escalado/vectorización) y
**DesignFabric** (generación de stickers vía Ollama + FLUX.2 Klein) en una sola app de
escritorio Electron, con un único backend FastAPI.

Todas las tools conviven como tabs de un mismo tabpane:

- Eliminación de fondo (ex-ClearCut)
- Escalado / vectorizado (ex-ClearCut)
- Procesamiento por lotes de ClearCut (ex-ClearCut)
- Generación por lotes con IA (ex-DesignFabric)
- Imagen única con IA (ex-DesignFabric)

Ver `AGENTS.md` para el detalle de arquitectura (capas del backend, feature registry,
workers GPU/CPU, y estructura del frontend por features).

## Comandos

```bash
# Setup
npm run setup                  # backend (uv sync) + frontend (npm install)

# Backend
cd backend
uv run uvicorn designfabricv2.api.app:app --reload --port 8756
uv run pytest

# CLIs standalone (no requieren Electron)
uv run clearcut remove ...
uv run designfabric --n 5

# Desktop app (arranca el backend automáticamente)
npm run dev
```
