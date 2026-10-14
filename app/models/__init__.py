"""The three detection branches.

`stub` mode returns deterministic fake scores derived from the video hash, so the
API, decision layer, audit log, Docker and CI all work before the real models are
wired in. Switch with TL_MODEL_MODE=real once `real.py` is filled in.
"""
from __future__ import annotations

from ..config import settings
from .base import Detector


def load_detectors() -> dict[str, Detector]:
    if settings.model_mode == "real":
        from .real import load_real_detectors
        return load_real_detectors(settings.weights_dir)
    from .stub import StubDetector
    return {name: StubDetector(name) for name in ("visual", "audio", "lipsync")}
