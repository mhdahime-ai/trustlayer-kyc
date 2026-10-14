"""FastAPI entry point.

POST /v1/verify          upload a KYC video -> decision + reasons + audit id
GET  /v1/decisions/{id}  fetch an audit record
GET  /v1/audit/verify    check the audit hash chain has not been tampered with
GET  /health
"""
from __future__ import annotations

import shutil
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from . import __version__
from .audit import AuditLog
from .config import load_policy, settings
from .decision import decide
from .media import MediaError, prepare
from .models import load_detectors
from .schemas import AuditRecord, BranchScores, MediaQuality, VerifyResponse

app = FastAPI(title="TrustLayer KYC", version=__version__,
              description="Deepfake defence for video-KYC: ALLOW / SOFT_WARN / ESCALATE / HARD_BLOCK")

policy = load_policy(settings.policy_path)
detectors = load_detectors()
audit = AuditLog(settings.audit_db)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "model_mode": settings.model_mode,
            "policy_version": policy.version}


@app.post("/v1/verify", response_model=VerifyResponse)
def verify(video: UploadFile = File(...), applicant_ref: str | None = Form(None)) -> VerifyResponse:
    t0 = time.perf_counter()
    tmp = Path(tempfile.mkdtemp(prefix="tl_up_"))
    path = tmp / "upload"
    try:
        size = 0
        with open(path, "wb") as f:
            while chunk := video.file.read(1 << 20):
                size += len(chunk)
                if size > settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(413, f"video larger than {settings.max_upload_mb} MB")
                f.write(chunk)

        try:
            media = prepare(path)
        except MediaError as e:
            raise HTTPException(422, str(e)) from e
        t_pre = time.perf_counter()

        try:
            scores = BranchScores(**{name: d.score(media) for name, d in detectors.items()})
            quality = MediaQuality(face_frames=detectors["visual"].face_frames(media),
                                   audio_seconds=round(media.audio_seconds, 2),
                                   duration_seconds=round(media.duration_seconds, 2))
        finally:
            media.cleanup()
        t_inf = time.perf_counter()

        result = decide(scores, quality, policy)
        decision_id = str(uuid.uuid4())
        audit.append({
            "decision_id": decision_id,
            "created_at": datetime.now(UTC).isoformat(),
            "applicant_ref": applicant_ref,
            "media_sha256": media.sha256,
            "decision": result.decision,
            "risk_score": result.risk_score,
            "branch_scores": scores.model_dump(),
            "reasons": result.reasons,
            "policy_version": policy.version,
            "model_mode": settings.model_mode,
        })
        t_end = time.perf_counter()

        return VerifyResponse(
            decision_id=decision_id,
            decision=result.decision,
            risk_score=result.risk_score,
            branch_scores=scores,
            quality=quality,
            reasons=result.reasons,
            policy_version=policy.version,
            model_mode=settings.model_mode,
            latency_ms={"preprocess": round((t_pre - t0) * 1000, 1),
                        "inference": round((t_inf - t_pre) * 1000, 1),
                        "total": round((t_end - t0) * 1000, 1)},
            media_sha256=media.sha256,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@app.get("/v1/decisions/{decision_id}", response_model=AuditRecord)
def get_decision(decision_id: str) -> AuditRecord:
    rec = audit.get(decision_id)
    if not rec:
        raise HTTPException(404, "decision not found")
    return rec


@app.get("/v1/audit/verify")
def verify_audit() -> dict:
    ok, n, bad = audit.verify_chain()
    return {"chain_intact": ok, "records_checked": n, "first_bad_seq": bad}
