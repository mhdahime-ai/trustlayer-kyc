"""Deterministic decision layer.

No ML here on purpose: given the same scores and the same policy you always get
the same decision and the same reasons. That is what auditors and regulators
want to see — the models give evidence, the rules make the call.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import Policy
from .schemas import BranchScores, Decision, MediaQuality

LABELS = {"visual": "face manipulation", "audio": "synthetic/spoofed voice",
          "lipsync": "lip movement does not match speech"}


@dataclass
class DecisionResult:
    decision: Decision
    risk_score: float
    reasons: list[str]


def fuse(scores: BranchScores, policy: Policy) -> float:
    s = scores.model_dump()
    return round(sum(policy.weights[k] * s[k] for k in policy.weights), 4)


def decide(scores: BranchScores, quality: MediaQuality, policy: Policy) -> DecisionResult:
    risk = fuse(scores, policy)
    s = scores.model_dump()
    reasons: list[str] = []

    strong = [k for k, v in s.items() if v >= policy.branch_hard_block]
    suspicious = [k for k, v in s.items() if v >= policy.branch_suspicious]
    for k in suspicious:
        reasons.append(f"{LABELS[k]} score {s[k]:.2f}")

    low_quality = []
    if quality.face_frames < policy.min_frames:
        low_quality.append(f"only {quality.face_frames} usable face frames (need {policy.min_frames})")
    if quality.audio_seconds < policy.min_audio_seconds:
        low_quality.append(f"only {quality.audio_seconds:.1f}s of speech (need {policy.min_audio_seconds}s)")

    # 1. Strong, corroborated evidence of a fake -> block
    if risk >= policy.hard_block and strong:
        reasons.insert(0, f"fused risk {risk:.2f} >= {policy.hard_block} with a high-confidence branch")
        return DecisionResult(Decision.HARD_BLOCK, risk, reasons)

    # 2. Enough doubt that a human must look
    if risk >= policy.escalate or len(suspicious) >= 2 or strong:
        why = (f"fused risk {risk:.2f} >= {policy.escalate}" if risk >= policy.escalate
               else "multiple branches suspicious" if len(suspicious) >= 2
               else "one branch highly confident but not corroborated")
        reasons.insert(0, why)
        return DecisionResult(Decision.ESCALATE, risk, reasons + low_quality)

    # 3. Mild risk, or we could not see/hear enough to be sure
    if risk >= policy.soft_warn or low_quality:
        if risk >= policy.soft_warn:
            reasons.insert(0, f"fused risk {risk:.2f} >= {policy.soft_warn}")
        return DecisionResult(Decision.SOFT_WARN, risk, reasons + low_quality)

    return DecisionResult(Decision.ALLOW, risk, [f"fused risk {risk:.2f} below {policy.soft_warn}"])
