"""Detección de hardware para backends de super-resolución."""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def _nvidia_smi_available() -> bool:
    if shutil.which("nvidia-smi") is None:
        return False
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def cuda_available() -> bool:
    """True si hay GPU CUDA usable (torch o nvidia-smi)."""
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return _nvidia_smi_available()

    try:
        if bool(torch.cuda.is_available()):
            return True
    except Exception:  # noqa: BLE001
        logger.debug("No se pudo consultar CUDA vía torch.", exc_info=True)

    return _nvidia_smi_available()
