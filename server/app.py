"""TwiBench web server: a JSON API around the Twi speech models, plus the
React front end (web/dist) served at "/".

Run:
    python server/app.py     # opens the app in your browser (first free port from 7860)

API:
    GET  /api/health                 models available, device
    GET  /api/examples?split=test&n=6
    GET  /api/audio/{split}/{name}   example audio (FLAC)
    POST /api/transcribe             form: file | (example_split, example_name), models, reference
    GET  /api/results                study metrics, error analysis, data stats
    POST /api/feedback               form: model, hypothesis, correction, consent, file?
"""
import csv
import os
import random
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import jiwer
import numpy as np
import pandas as pd
import soundfile as sf
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from error_analysis import FOLD, boundary_words, is_loan  # noqa: E402
from normalize import normalize  # noqa: E402

SR = 16_000
MAX_SECONDS = 30
PROCESSED = ROOT / "data" / "processed"
FEEDBACK_DIR = ROOT / "data" / "feedback"

MODELS = {
    # Local folder by default; on a hosted Space set TWIBENCH_MODEL to a Hub id, e.g. "user/whisper-small-twi".
    "finetuned": {"label": "TwiBench fine-tuned",
                  "path": os.environ.get("TWIBENCH_MODEL") or ROOT / "models" / "whisper-small-twi",
                  "language": "yoruba"},
    "zeroshot": {"label": "Original Whisper-small", "path": "openai/whisper-small", "language": None},
}
SPLITS = {"test": "Asante Twi (finance)", "ood_test": "Scripture readings"}

app = FastAPI(title="TwiBench")
_loaded, _load_lock, _infer_lock = {}, threading.Lock(), threading.Lock()


# ---------------------------------------------------------------- models
def available(key):
    path = MODELS[key]["path"]
    if key == "zeroshot" or (isinstance(path, str) and not Path(path).exists()):
        return True  # downloaded from the Hugging Face Hub on first use
    return (Path(path) / "model.safetensors").exists()


def get_model(key):
    with _load_lock:
        if key not in _loaded:
            from evaluate import WhisperASR
            cfg = MODELS[key]
            _loaded[key] = WhisperASR(str(cfg["path"]), cfg["language"])
        return _loaded[key]


def decode(data: bytes) -> np.ndarray:
    """Any audio format (webm/ogg from the browser, wav, mp3, flac...) -> 16 kHz mono float32."""
    try:
        out = subprocess.run(
            ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", "pipe:0",
             "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
            input=data, capture_output=True, check=True, timeout=60).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        raise HTTPException(400, "Could not read that audio file.")
    y = np.frombuffer(out, dtype=np.float32)
    if len(y) < SR * 0.2:
        raise HTTPException(400, "The recording is too short (or silent).")
    return y[:SR * MAX_SECONDS]


# ---------------------------------------------------------------- scoring
def compare(reference: str, hypothesis: str) -> dict:
    """WER/CER plus a word-by-word alignment with error types, for the UI."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return None
    out = jiwer.process_words(ref, hyp or "")
    rw, hw = out.references[0], out.hypotheses[0]
    b_ref, b_hyp = boundary_words(rw, hw)
    ops = []
    for a in out.alignments[0]:
        ri = list(range(a.ref_start_idx, a.ref_end_idx))
        hi = list(range(a.hyp_start_idx, a.hyp_end_idx))
        if a.type == "equal":
            ops += [{"op": "equal", "ref": rw[i], "hyp": hw[j]} for i, j in zip(ri, hi)]
        elif a.type == "substitute":
            for i, j in zip(ri, hi):
                kind = ("boundary" if i in b_ref or j in b_hyp
                        else "vowel" if rw[i].translate(FOLD) == hw[j].translate(FOLD)
                        else "loanword" if is_loan(rw[i]) else "other")
                ops.append({"op": "substitute", "ref": rw[i], "hyp": hw[j], "kind": kind})
        elif a.type == "delete":
            ops += [{"op": "delete", "ref": rw[i], "kind": "boundary" if i in b_ref else "other"} for i in ri]
        else:
            ops += [{"op": "insert", "hyp": hw[j], "kind": "boundary" if j in b_hyp else "other"} for j in hi]
    return {"wer": jiwer.wer(ref, hyp or ""), "cer": jiwer.cer(ref, hyp or ""),
            "words": len(rw), "ops": ops}


# ---------------------------------------------------------------- examples
def manifest(split):
    f = PROCESSED / f"{split}.csv"
    if split not in SPLITS or not f.exists():
        raise HTTPException(404, "Unknown example set.")
    return pd.read_csv(f)


@app.get("/api/health")
def health():
    return {"models": [{"key": k, "label": v["label"], "available": available(k), "loaded": k in _loaded}
                       for k, v in MODELS.items()],
            "splits": [{"key": k, "label": v} for k, v in SPLITS.items() if (PROCESSED / f"{k}.csv").exists()],
            "max_seconds": MAX_SECONDS}


@app.get("/api/examples")
def examples(split: str = "test", n: int = 6, seed: int | None = None):
    df = manifest(split)
    df = df[df["duration"].between(1.0, MAX_SECONDS)]
    df = df.sample(frac=1, random_state=seed).drop_duplicates("text")  # distinct sentences
    rows = df.sample(n=min(n, len(df)), random_state=seed if seed is not None else random.randrange(10**6))
    return [{"split": split, "name": Path(r["audio"]).name, "text": r["text"],
             "duration": round(float(r["duration"]), 1),
             "speaker": r.get("gender") if isinstance(r.get("gender"), str) else None,
             "url": f"/api/audio/{split}/{Path(r['audio']).name}"} for _, r in rows.iterrows()]


@app.get("/api/audio/{split}/{name}")
def audio(split: str, name: str):
    path = (PROCESSED / "audio" / split / name).resolve()
    if split not in SPLITS or path.parent != (PROCESSED / "audio" / split).resolve() or not path.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="audio/flac")


# ---------------------------------------------------------------- transcribe
@app.post("/api/transcribe")
async def transcribe(file: UploadFile | None = File(None), example_split: str = Form(""),
                     example_name: str = Form(""), models: str = Form("finetuned"),
                     reference: str = Form("")):
    if file is not None:
        y = decode(await file.read())
    elif example_split and example_name:
        df = manifest(example_split)
        row = df[df["audio"].map(lambda p: Path(p).name) == example_name]
        if row.empty:
            raise HTTPException(404, "Example not found.")
        y = sf.read(ROOT / row.iloc[0]["audio"], dtype="float32")[0]
        reference = reference or row.iloc[0]["text"]
    else:
        raise HTTPException(400, "Send a recording, an audio file, or pick an example.")

    keys = [k for k in models.split(",") if k in MODELS and available(k)] or ["zeroshot"]
    results = []
    for key in keys:
        asr = get_model(key)
        t0 = time.time()
        with _infer_lock:  # one transcription at a time on CPU
            text = asr([y])[0].strip()
        results.append({"model": key, "label": MODELS[key]["label"], "text": text,
                        "seconds": round(time.time() - t0, 1), "score": compare(reference, text)})
    return {"duration": round(len(y) / SR, 1), "reference": reference or None, "results": results}


# ---------------------------------------------------------------- results
def read_csv(path):
    return pd.read_csv(path).replace({np.nan: None}).to_dict("records") if path.exists() else []


@app.get("/api/results")
def results():
    ea = ROOT / "results" / "error_analysis"
    perfect = {}  # share of clips transcribed with zero word errors, per "model/split"
    for f in (ROOT / "results" / "predictions").glob("*__*.csv"):
        model, split = f.stem.split("__")
        w = pd.read_csv(f)["wer"].dropna()
        perfect[f"{model}/{split}"] = float((w == 0).mean()) if len(w) else None
    return {"metrics": read_csv(ROOT / "results" / "metrics.csv"),
            "errors": read_csv(ea / "summary.csv"),
            "data": read_csv(ROOT / "results" / "data_stats.csv"),
            "perfect": perfect}


# ---------------------------------------------------------------- feedback
@app.post("/api/feedback")
async def feedback(model: str = Form(...), hypothesis: str = Form(""), correction: str = Form(...),
                   consent: bool = Form(False), file: UploadFile | None = File(None)):
    correction = correction.strip()
    if not correction:
        raise HTTPException(400, "Please type the correct text.")
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    audio_name = ""
    if consent and file is not None:  # audio is stored only with explicit consent
        y = decode(await file.read())
        audio_name = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}.flac"
        sf.write(FEEDBACK_DIR / audio_name, y, SR)
    log = FEEDBACK_DIR / "feedback.csv"
    new = not log.exists()
    with open(log, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "model", "hypothesis", "correction", "audio"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), model, hypothesis, correction, audio_name])
    return {"saved": True, "audio_saved": bool(audio_name)}


# ---------------------------------------------------------------- front end
DIST = ROOT / "web" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
else:
    @app.get("/")
    def no_frontend():
        return {"message": "Front end not built yet: run `npm install` and `npm run build` in web/."}


def free_port(start: int) -> int:
    """First port from `start` that nothing else is listening on."""
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit("No free port found.")


if __name__ == "__main__":
    host = os.environ.get("TWIBENCH_HOST", "127.0.0.1")   # 0.0.0.0 inside a hosted container
    port = int(os.environ.get("TWIBENCH_PORT", 7860))
    if host == "127.0.0.1":
        port = free_port(port)  # on a PC, skip ports other apps already use
    url = f"http://127.0.0.1:{port}"
    print(f"\n  TwiBench is running: open {url} in your browser\n", flush=True)
    if os.environ.get("TWIBENCH_OPEN", "1") == "1":
        threading.Timer(1.5, lambda: __import__("webbrowser").open(url)).start()
    uvicorn.run(app, host=host, port=port)
