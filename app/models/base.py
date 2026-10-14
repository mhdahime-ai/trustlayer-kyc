from __future__ import annotations

from typing import Protocol

from ..media import PreparedMedia


class Detector(Protocol):
    name: str

    def face_frames(self, media: PreparedMedia) -> int:  # only the visual branch needs to override
        ...

    def score(self, media: PreparedMedia) -> float:
        """Return probability in [0, 1] that the media is fake for this branch."""
        ...
