import pytest

from app.config import ROOT, load_policy
from app.decision import decide, fuse
from app.schemas import BranchScores, Decision, MediaQuality

POLICY = load_policy(ROOT / "policy.yaml")
GOOD_Q = MediaQuality(face_frames=50, audio_seconds=8, duration_seconds=10)


def run(v, a, ls, q=GOOD_Q):
    return decide(BranchScores(visual=v, audio=a, lipsync=ls), q, POLICY)


def test_weights_fuse():
    assert fuse(BranchScores(visual=1, audio=1, lipsync=1), POLICY) == 1.0


@pytest.mark.parametrize("scores,expected", [
    ((0.05, 0.10, 0.08), Decision.ALLOW),
    ((0.40, 0.40, 0.30), Decision.SOFT_WARN),
    ((0.70, 0.60, 0.20), Decision.ESCALATE),     # fused 0.52 but two branches suspicious
    ((0.95, 0.10, 0.10), Decision.ESCALATE),     # one strong branch, not corroborated
    ((0.95, 0.85, 0.75), Decision.HARD_BLOCK),
])
def test_decision_table(scores, expected):
    assert run(*scores).decision == expected


def test_low_quality_never_allows():
    q = MediaQuality(face_frames=2, audio_seconds=0.2, duration_seconds=1)
    r = run(0.01, 0.01, 0.01, q)
    assert r.decision == Decision.SOFT_WARN
    assert any("face frames" in x for x in r.reasons)


def test_deterministic():
    assert run(0.6, 0.6, 0.6) == run(0.6, 0.6, 0.6)


def test_every_decision_has_reasons():
    for s in [(0.0, 0.0, 0.0), (0.4, 0.4, 0.3), (0.7, 0.6, 0.2), (0.95, 0.85, 0.75)]:
        assert run(*s).reasons
