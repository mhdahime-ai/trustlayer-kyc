# TrustLayer KYC — Deepfake defence for video-KYC
   [![CI](https://github.com/mhdahime-ai/trustlayer-kyc/actions/workflows/ci.yml/badge.svg)](https://github.com/mhdahime-ai/trustlayer-kyc/actions/workflows/ci.yml)

A production-style API that checks a video-KYC recording for deepfakes and returns one of four
decisions a bank can act on: **ALLOW**, **SOFT_WARN**, **ESCALATE** (human review) or **HARD_BLOCK**,
with plain reasons and a tamper-evident audit trail.

Built on my MSc dissertation (TrustLayer AI, F1 0.735 on FakeAVCeleb v1.2), turned from a research
model into a service a regulated institution could deploy.

## Why this exists

Video-KYC lets customers open accounts remotely. Face-swaps and cloned voices can now pass a casual
human check. Banks need a second line of defence that is **explainable, auditable and self-hostable**
— a black-box score from a third-party API is hard to defend to a regulator and sends customer
biometrics outside the institution.

## How it works

```
 video ──► ffmpeg ──► frames (5 fps) ──► Visual branch (CNN)         ─┐
                 └──► 16 kHz audio  ──► Audio branch (anti-spoofing) ─┼─► weighted fusion ─► rule-based decision ─► audit log
                       frames+audio ──► Lip-sync branch (landmarks)  ─┘          (policy.yaml)     + reasons          (hash chain)
```

- **Models give evidence, rules make the call.** The decision layer is deterministic: same scores +
  same policy = same decision and same reasons, every time.
- **Policy as config.** Weights and thresholds live in `policy.yaml`, versioned. Every decision records
  which policy version made it.
- **Quality gate.** Too few face frames or too little speech can never produce ALLOW.
- **Tamper-evident audit log.** Each record contains the hash of the previous one. Editing any past
  decision breaks the chain; `GET /v1/audit/verify` detects it.
- **Privacy by design.** The video is deleted after scoring; only its SHA-256 is stored.

## Decision rules

| Decision | When |
|---|---|
| HARD_BLOCK | fused risk ≥ 0.80 **and** at least one branch ≥ 0.90 |
| ESCALATE | fused risk ≥ 0.60, or two branches ≥ 0.50, or one very confident branch not backed up by the others |
| SOFT_WARN | fused risk ≥ 0.35, or media quality too low to judge |
| ALLOW | everything else |

## Run it

```bash
docker compose up --build
curl -F video=@sample.mp4 -F applicant_ref=APP-123 localhost:8000/v1/verify
```

Interactive docs at http://localhost:8000/docs.

Without Docker:

```bash
pip install -r requirements-dev.txt     # needs ffmpeg on PATH
uvicorn app.main:app --reload
pytest -q
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/verify` | Upload a video → decision, risk score, per-branch scores, reasons, latency |
| GET | `/v1/decisions/{id}` | Retrieve an audit record |
| GET | `/v1/audit/verify` | Check the audit chain has not been tampered with |
| GET | `/health` | Service, model mode and policy version |

## Model modes

- `TL_MODEL_MODE=stub` (default) — deterministic placeholder scores so the whole system runs and is testable.
- `TL_MODEL_MODE=real` — loads `weights/visual.onnx`, `audio.onnx`, `lipsync.onnx` (see `app/models/real.py`).

## Results

_To fill in once real models are wired in:_

| Metric | Value |
|---|---|
| F1 / AUC on FakeAVCeleb test split | |
| Decision distribution on test set (ALLOW / SOFT_WARN / ESCALATE / HARD_BLOCK) | |
| % of fakes reaching ALLOW (the number a bank cares about most) | |
| p50 / p95 latency, 10 s clip, CPU | |
| Container size | |

## Limitations

Trained on one public dataset; new generation methods will need retraining. Not a replacement for
liveness checks. Thresholds should be tuned on the institution's own traffic.
