"""Settings and decision policy loading.

The policy (weights + thresholds) lives in policy.yaml so a compliance team can
change it without touching code. Every decision records the policy version used.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Policy:
    version: str
    weights: dict[str, float]
    soft_warn: float
    escalate: float
    hard_block: float
    branch_hard_block: float
    branch_suspicious: float
    min_frames: int = 8
    min_audio_seconds: float = 1.0
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Settings:
    policy_path: Path = Path(os.getenv("TL_POLICY_PATH", ROOT / "policy.yaml"))
    audit_db: Path = Path(os.getenv("TL_AUDIT_DB", ROOT / "data" / "audit.db"))
    model_mode: str = os.getenv("TL_MODEL_MODE", "stub")  # "stub" | "real"
    weights_dir: Path = Path(os.getenv("TL_WEIGHTS_DIR", ROOT / "weights"))
    max_upload_mb: int = int(os.getenv("TL_MAX_UPLOAD_MB", "50"))


def load_policy(path: Path) -> Policy:
    raw = yaml.safe_load(Path(path).read_text())
    t = raw["thresholds"]
    weights = raw["weights"]
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"policy weights must sum to 1.0, got {total}")
    return Policy(
        version=str(raw["version"]),
        weights=weights,
        soft_warn=t["soft_warn"],
        escalate=t["escalate"],
        hard_block=t["hard_block"],
        branch_hard_block=t["branch_hard_block"],
        branch_suspicious=t["branch_suspicious"],
        min_frames=raw.get("quality", {}).get("min_frames", 8),
        min_audio_seconds=raw.get("quality", {}).get("min_audio_seconds", 1.0),
    )


settings = Settings()
