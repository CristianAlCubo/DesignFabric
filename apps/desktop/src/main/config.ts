/**
 * Configuración del proceso `main`: puerto y URL base del backend FastAPI.
 *
 * El backend (`backend/src/designfabric/core/config.py`) usa
 * `pydantic_settings` con `env_prefix="DESIGNFABRIC_"` (NO `DESIGNFABRIC_` —
 * el prefijo de env var no se renombró durante la fusión, ver `Settings.model_config`).
 * Por eso usamos aquí la misma variable `DESIGNFABRIC_API_PORT` al lanzar el
 * proceso hijo `uv run uvicorn`, para que main/renderer y backend coincidan.
 */

const DEFAULT_PORT = 8756

export const backendPort = Number(process.env.DESIGNFABRIC_API_PORT ?? DEFAULT_PORT)

export const backendBaseUrl = `http://127.0.0.1:${backendPort}`
