import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
import app as server  # noqa: E402

client = TestClient(server.app)


def test_compare_marks_error_types():
    s = server.compare("Mɛtɔ credit", "meto kredit")
    assert s["words"] == 2 and s["wer"] == 1.0
    assert [o["kind"] for o in s["ops"]] == ["vowel", "loanword"]
    assert server.compare("", "anything") is None


def test_compare_perfect_and_boundary():
    assert server.compare("Ɛkɔm de me.", "ɛkɔm de me")["wer"] == 0
    kinds = {o.get("kind") for o in server.compare("melki ba", "melkiba")["ops"]}
    assert kinds == {"boundary"}


def test_health_and_results():
    h = client.get("/api/health").json()
    assert {m["key"] for m in h["models"]} == {"finetuned", "zeroshot"}
    r = client.get("/api/results").json()
    assert set(r) == {"metrics", "errors", "data", "perfect"}


@pytest.mark.skipif(not (ROOT / "data/processed/test.csv").exists(), reason="no local test data")
def test_examples_are_distinct_and_playable():
    ex = client.get("/api/examples?split=test&n=6&seed=3").json()
    assert len({e["text"] for e in ex}) == len(ex)
    assert client.get(ex[0]["url"]).status_code == 200


def test_audio_path_traversal_blocked():
    assert client.get("/api/audio/test/..%2F..%2Fmetadata.csv").status_code == 404
    assert client.get("/api/audio/secret/x.flac").status_code == 404


def test_bad_audio_and_empty_request():
    assert client.post("/api/transcribe", files={"file": ("x.webm", b"not audio")}).status_code == 400
    assert client.post("/api/transcribe", data={"models": "finetuned"}).status_code == 400


def test_feedback_requires_text():
    assert client.post("/api/feedback", data={"model": "finetuned", "correction": "  "}).status_code == 400
