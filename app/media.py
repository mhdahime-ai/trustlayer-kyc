"""Turn an uploaded video into the inputs the three branches need.

Uses ffmpeg/ffprobe (installed in the Docker image):
  - frames sampled at FPS into a temp folder  -> visual + lip-sync branches
  - 16 kHz mono WAV                            -> audio + lip-sync branches
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

FPS = 5


class MediaError(ValueError):
    pass


@dataclass
class PreparedMedia:
    workdir: Path
    frames: list[Path]
    wav: Path | None
    duration_seconds: float
    audio_seconds: float
    sha256: str

    def cleanup(self) -> None:
        shutil.rmtree(self.workdir, ignore_errors=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        raise MediaError("file is not a readable video")
    return json.loads(out.stdout)


def prepare(video: Path) -> PreparedMedia:
    info = _probe(video)
    streams = info.get("streams", [])
    if not any(s.get("codec_type") == "video" for s in streams):
        raise MediaError("no video stream found")
    duration = float(info.get("format", {}).get("duration", 0) or 0)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    work = Path(tempfile.mkdtemp(prefix="tl_"))
    frames_dir = work / "frames"
    frames_dir.mkdir()
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={FPS}", str(frames_dir / "%05d.jpg")],
        check=True,
    )
    wav = None
    audio_seconds = 0.0
    if has_audio:
        wav = work / "audio.wav"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
            check=True,
        )
        # TODO: replace with voice-activity detection (e.g. silero-vad) to count real speech only
        audio_seconds = float(_probe(wav)["format"].get("duration", 0) or 0)

    return PreparedMedia(
        workdir=work,
        frames=sorted(frames_dir.glob("*.jpg")),
        wav=wav,
        duration_seconds=duration,
        audio_seconds=audio_seconds,
        sha256=sha256_file(video),
    )
