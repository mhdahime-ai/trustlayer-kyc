"""Wire your TrustLayer dissertation models in here.

Plan (do these in order):
  1. Export each trained branch to ONNX:
       torch.onnx.export(model, dummy_input, "weights/visual.onnx", opset_version=17)
  2. Copy the exact preprocessing you used in training (face crop size, normalisation,
     MFCC / spectrogram settings, lip-landmark extractor) into the methods below.
  3. Add a parity test in tests/: the ONNX output must match the PyTorch output on
     the same inputs (tolerance ~1e-4) before you trust it.
  4. Set TL_MODEL_MODE=real.
"""
from __future__ import annotations

from pathlib import Path

from ..media import PreparedMedia


class OnnxBranch:
    def __init__(self, name: str, onnx_path: Path):
        import onnxruntime as ort  # imported lazily so stub mode needs no ONNX install

        self.name = name
        self.session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

    def face_frames(self, media: PreparedMedia) -> int:
        # TODO (visual branch): run a face detector (e.g. OpenCV DNN / MediaPipe) and count
        # frames with exactly one face. Other branches can return len(media.frames).
        return len(media.frames)

    def score(self, media: PreparedMedia) -> float:
        # TODO: build the input tensor exactly as in training, run self.session.run(...),
        # aggregate per-frame / per-window outputs (mean or top-k mean) into one probability.
        raise NotImplementedError(f"{self.name}: plug in your preprocessing + inference")


def load_real_detectors(weights_dir: Path) -> dict[str, OnnxBranch]:
    return {name: OnnxBranch(name, weights_dir / f"{name}.onnx") for name in ("visual", "audio", "lipsync")}
