"""Builds twibench.ipynb: one notebook that runs the whole pipeline on
Kaggle (data prep, baselines, fine-tuning, evaluation), so nothing heavy is
downloaded to the local PC. The src/*.py files are embedded verbatim, so the
notebook always runs exactly the code in this repo.

Run after any change in src/:
    python notebooks/build_notebook.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_FILES = ["normalize.py", "prepare_data.py", "prepare_ood.py", "evaluate.py", "finetune_whisper.py"]

INTRO = """# TwiBench — full pipeline (Google Colab or Kaggle)

**Google Colab:** *Runtime → Change runtime type → **T4 GPU** → Save*, then *Runtime → Run all*.
At the end, results are saved to your Google Drive in `MyDrive/TwiBench/` (Colab asks once for Drive access).
Keep the browser tab open while it runs.

**Kaggle:** *Session options → Accelerator: GPU*, *Internet: On*, then *Run All*.
Results appear in the *Output* panel.

`twibench_results.zip` (a few MB: metrics, predictions, data stats, training log) is what you
unzip into the project folder on your PC. Total time is about 3–5 hours, most of it fine-tuning.
Use `MAX_STEPS = 200` in the next cell for a quick test run first (~30–40 min)."""

SETTINGS = """RUN_BASELINES = True     # zero-shot Whisper-small and MMS (aka adapter)
RUN_FINETUNE  = True     # fine-tune Whisper-small, then evaluate it
MAX_STEPS     = 4000     # use 200 for a quick test run
SAVE_MODEL_ZIP = True    # ~1 GB zip of the fine-tuned model (needed later for the demo)

import os, torch
IN_COLAB = "COLAB_RELEASE_TAG" in os.environ
OUT_DIR = "/kaggle/working" if os.path.isdir("/kaggle/working") else os.getcwd()
if IN_COLAB:
    from google.colab import drive
    drive.mount("/content/drive")
    OUT_DIR = "/content/drive/MyDrive/TwiBench"
os.makedirs(OUT_DIR, exist_ok=True)
assert torch.cuda.is_available(), "No GPU: switch the runtime/accelerator to a GPU first"
print("GPU:", torch.cuda.get_device_name(0), "| results will be saved to", OUT_DIR)"""

STEPS = [
    ("md", "## 1. Install"),
    ("code", '!pip install -q "transformers==5.20.1" "accelerate>=0.34" "jiwer>=3.0" soundfile librosa'),
    ("md", "## 2. Data: download, speaker- and sentence-disjoint split, out-of-domain set"),
    ("code", "!python src/prepare_data.py\n!python src/prepare_ood.py"),
    ("md", "## 3. Zero-shot baselines"),
    ("code", """if RUN_BASELINES:
    for model in ["whisper-small", "mms"]:
        for split in ["test", "ood_test"]:
            !python src/evaluate.py --model {model} --split {split} --batch-size 16"""),
    ("md", "## 4. Fine-tune Whisper-small and evaluate it"),
    ("code", """if RUN_FINETUNE:
    !python src/finetune_whisper.py --output models/whisper-small-twi --max-steps {MAX_STEPS}
    for split in ["test", "ood_test"]:
        !python src/evaluate.py --model models/whisper-small-twi --kind whisper --tag whisper-small-ft --language yoruba --split {split} --batch-size 16"""),
    ("md", "## 5. Package results for download"),
    ("code", """import shutil, glob, pandas as pd
shutil.copy("data/processed/metadata.csv", "results/metadata.csv")
for f in glob.glob("models/whisper-small-twi/training_log.csv"):
    shutil.copy(f, "results/training_log.csv")
shutil.make_archive(f"{OUT_DIR}/twibench_results", "zip", "results")
if RUN_FINETUNE and SAVE_MODEL_ZIP:
    for d in glob.glob("models/whisper-small-twi/checkpoint-*"):
        shutil.rmtree(d)
    shutil.make_archive(f"{OUT_DIR}/whisper-small-twi", "zip", "models/whisper-small-twi")
if not IN_COLAB:  # on Kaggle, keep Output small
    shutil.rmtree("data", ignore_errors=True)
    shutil.rmtree("models", ignore_errors=True)
print("Saved to", OUT_DIR, os.listdir(OUT_DIR))
pd.read_csv("results/metrics.csv")"""),
]


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": src.splitlines(keepends=True)}


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}


def main():
    cells = [md(INTRO), code(SETTINGS), md("## 0. Project code (generated from `src/`)")]
    cells.append(code("import os\nos.makedirs('src', exist_ok=True)\nos.makedirs('results', exist_ok=True)"))
    for name in SRC_FILES:
        cells.append(code(f"%%writefile src/{name}\n" + (ROOT / "src" / name).read_text(encoding="utf-8")))
    for kind, src in STEPS:
        cells.append(md(src) if kind == "md" else code(src))

    nb = {"cells": cells,
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                       "accelerator": "GPU"},
          "nbformat": 4, "nbformat_minor": 5}
    out = Path(__file__).with_name("twibench.ipynb")
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
