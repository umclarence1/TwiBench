"""Unattended run of the remaining steps on this PC (CPU):

    1. fine-tune Whisper-small (decoder only) for a fixed time budget
    2. evaluate the fine-tuned model on the in-domain and out-of-domain tests
    3. run any missing zero-shot baselines
    4. run the error analysis
Steps run one at a time so they don't compete for the CPU.

Keeps Windows awake while it runs (no settings are changed; normal sleep
returns when the script ends). Progress goes to results/overnight_log.txt.

Usage:
    python src/run_overnight.py [--hours 5]
"""
import argparse
import ctypes
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
LOG = ROOT / "results" / "overnight_log.txt"
MODEL_DIR = ROOT / "models" / "whisper-small-twi"


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def keep_awake():
    if sys.platform == "win32":
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


def has_result(model, split):
    f = ROOT / "results" / "metrics.csv"
    if not f.exists():
        return False
    m = pd.read_csv(f)
    return bool(((m["model"] == model) & (m["split"] == split)).any())


def run(step, args):
    log(f"START {step}")
    t0 = time.time()
    with open(ROOT / "results" / f"log_{step}.txt", "w", encoding="utf-8") as out:
        code = subprocess.call([PY, *args], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
    log(f"END   {step}: exit {code} after {(time.time() - t0) / 60:.0f} min")
    return code == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=4.0, help="fine-tuning time budget")
    args = ap.parse_args()
    keep_awake()
    log("overnight run started")

    # 1. Fine-tune first: it is the longest and most important step.
    #    (skipped if a finished model already exists)
    if not (MODEL_DIR / "model.safetensors").exists():
        ok = run("finetune", [
            "src/finetune_whisper.py", "--data", "local", "--freeze-encoder",
            "--output", str(MODEL_DIR), "--batch-size", "8", "--grad-accum", "1",
            "--lr", "5e-5", "--warmup-steps", "30", "--max-steps", "5000",
            "--max-hours", str(args.hours), "--dev-clips", "40", "--eval-steps", "100000",
        ])
        if not ok:
            log("fine-tuning failed; see results/log_finetune.txt. Stopping.")
            return

    # 2. Evaluate the fine-tuned model, one job at a time
    for split in ["test", "ood_test"]:
        run(f"eval_ft_{split}", [
            "src/evaluate.py", "--model", str(MODEL_DIR), "--kind", "whisper",
            "--tag", "whisper-small-ft", "--language", "yoruba", "--split", split, "--batch-size", "16",
        ])

    # 3. Zero-shot baseline on the out-of-domain sample (in-domain was done earlier)
    for split in ["test", "ood_test"]:
        if not has_result("whisper-small", split):
            run(f"eval_zeroshot_{split}", ["src/evaluate.py", "--model", "whisper-small",
                                           "--split", split, "--batch-size", "16"])

    # 4. Error analysis
    run("error_analysis", ["src/error_analysis.py"])
    log("overnight run finished")


if __name__ == "__main__":
    main()
