from __future__ import annotations

import hashlib

from ..media import PreparedMedia


class StubDetector:
    """Deterministic placeholder: same video -> same score. NOT a real detector."""

    def __init__(self, name: str):
        self.name = name

    def face_frames(self, media: PreparedMedia) -> int:
        return len(media.frames)  # assumes every frame has a face

    def score(self, media: PreparedMedia) -> float:
        h = hashlib.sha256((self.name + media.sha256).encode()).hexdigest()
        return round(int(h[:8], 16) / 0xFFFFFFFF, 4)
