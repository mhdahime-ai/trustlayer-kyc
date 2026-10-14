from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Decision(StrEnum):
    ALLOW = "ALLOW"
    SOFT_WARN = "SOFT_WARN"
    ESCALATE = "ESCALATE"
    HARD_BLOCK = "HARD_BLOCK"


class MediaQuality(BaseModel):
    face_frames: int = Field(..., description="Frames where a face was found")
    audio_seconds: float = Field(..., description="Seconds of usable speech")
    duration_seconds: float


class BranchScores(BaseModel):
    """Each score is a probability-like value in [0, 1]; higher = more likely fake."""
    visual: float = Field(..., ge=0, le=1)
    audio: float = Field(..., ge=0, le=1)
    lipsync: float = Field(..., ge=0, le=1)


class VerifyResponse(BaseModel):
    decision_id: str
    decision: Decision
    risk_score: float
    branch_scores: BranchScores
    quality: MediaQuality
    reasons: list[str]
    policy_version: str
    model_mode: str
    latency_ms: dict[str, float]
    media_sha256: str


class AuditRecord(BaseModel):
    decision_id: str
    created_at: str
    applicant_ref: str | None
    media_sha256: str
    decision: Decision
    risk_score: float
    branch_scores: BranchScores
    reasons: list[str]
    policy_version: str
    model_mode: str
    prev_hash: str
    record_hash: str
