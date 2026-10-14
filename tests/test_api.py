from fastapi.testclient import TestClient

from app.main import app, audit

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["model_mode"] == "stub"


def test_verify_and_audit(sample_video):
    with open(sample_video, "rb") as f:
        r = client.post("/v1/verify", files={"video": ("s.mp4", f, "video/mp4")},
                        data={"applicant_ref": "TEST-001"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["decision"] in {"ALLOW", "SOFT_WARN", "ESCALATE", "HARD_BLOCK"}
    assert body["reasons"]
    assert body["quality"]["face_frames"] >= 10

    rec = client.get(f"/v1/decisions/{body['decision_id']}").json()
    assert rec["media_sha256"] == body["media_sha256"]
    assert rec["applicant_ref"] == "TEST-001"


def test_same_video_same_decision(sample_video):
    outs = []
    for _ in range(2):
        with open(sample_video, "rb") as f:
            outs.append(client.post("/v1/verify", files={"video": ("s.mp4", f, "video/mp4")}).json())
    assert outs[0]["decision"] == outs[1]["decision"]
    assert outs[0]["branch_scores"] == outs[1]["branch_scores"]


def test_rejects_non_video():
    r = client.post("/v1/verify", files={"video": ("x.mp4", b"not a video", "video/mp4")})
    assert r.status_code == 422


def test_tamper_detected():
    assert client.get("/v1/audit/verify").json()["chain_intact"] is True
    # simulate someone quietly editing a past decision
    audit.conn.execute("UPDATE decisions SET payload = replace(payload, 'ESCALATE', 'ALLOW') WHERE seq = 1")
    audit.conn.execute("UPDATE decisions SET payload = payload || ' ' WHERE seq = 1")
    audit.conn.commit()
    res = client.get("/v1/audit/verify").json()
    assert res["chain_intact"] is False
    assert res["first_bad_seq"] == 1
