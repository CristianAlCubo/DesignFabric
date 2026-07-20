"""Backends de super-resolución por IA."""

from designfabric.core.imaging.ai_upscalers.realesrgan import RealEsrganBackend

# SpanBackend desactivado; ver ai_upscalers/span.py

__all__ = ["RealEsrganBackend"]
