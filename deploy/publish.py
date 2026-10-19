"""Host TwiBench on Hugging Face Spaces (free).

    1. Model repo  <user>/whisper-small-twi   : the fine-tuned model (~930 MB, uploaded once)
    2. Space       <user>/twibench            : the web app (Docker), ~40 MB

Step 0 (once): create a free account at huggingface.co, make a WRITE token at
huggingface.co/settings/tokens, then run:  .venv\\Scripts\\hf auth login

Usage:
    python deploy/publish.py --user YOUR_HF_USERNAME --dry-run   # only stage files, upload nothing
    python deploy/publish.py --user YOUR_HF_USERNAME             # upload model + app
    python deploy/publish.py --user YOUR_HF_USERNAME --app-only  # update the app, keep the model
"""
import argparse
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "deploy" / "_space"

SPACE_CARD = """---
title: TwiBench
emoji: 🎙️
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Speak Twi, see it written. Speech recognition for Twi.
---

# TwiBench: speech recognition for Twi

Speak Twi and see it written. Whisper-small fine-tuned on Asante Twi
(Ashesi Financial Inclusion Speech Dataset, CC-BY-4.0), with a before/after comparison,
word-level feedback and the study's results.

Model: [{model}](https://huggingface.co/{model})
"""

MODEL_CARD = """---
language: tw
license: mit
base_model: openai/whisper-small
tags: [automatic-speech-recognition, whisper, twi, akan]
---

# Whisper-small fine-tuned on Asante Twi (TwiBench)

Decoder-only fine-tune of `openai/whisper-small` on ~2.5 h of Asante Twi
(Ashesi Financial Inclusion Speech Dataset, CC-BY-4.0), evaluated on a speaker- and
sentence-disjoint test set.

| Test set | WER before | WER after | CER after |
|---|---|---|---|
| Asante Twi (234 clips) | {zs:.1%} | {ft:.1%} | {ft_cer:.1%} |

Twi is not a Whisper language: generate with `language="yoruba"` as a proxy token,
as used in training.
"""


def stage(model_id: str):
    """Copy only what the hosted app needs into deploy/_space."""
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    for f in ["Dockerfile", "requirements.txt"]:
        shutil.copy(ROOT / "deploy" / f, STAGE / f)
    (STAGE / "README.md").write_text(SPACE_CARD.format(model=model_id), encoding="utf-8")

    for f in ["normalize.py", "evaluate.py", "error_analysis.py"]:
        (STAGE / "src").mkdir(exist_ok=True)
        shutil.copy(ROOT / "src" / f, STAGE / "src" / f)
    (STAGE / "server").mkdir()
    shutil.copy(ROOT / "server" / "app.py", STAGE / "server" / "app.py")

    web = STAGE / "web"
    shutil.copytree(ROOT / "web", web, ignore=shutil.ignore_patterns("node_modules", "dist"))

    res = STAGE / "results"
    (res / "error_analysis").mkdir(parents=True)
    for f in ["metrics.csv", "data_stats.csv"]:
        shutil.copy(ROOT / "results" / f, res / f)
    shutil.copy(ROOT / "results" / "error_analysis" / "summary.csv", res / "error_analysis" / "summary.csv")
    shutil.copytree(ROOT / "results" / "predictions", res / "predictions")

    # Example clips: only the ones the manifests reference
    for split in ["test", "ood_test"]:
        df = pd.read_csv(ROOT / "data" / "processed" / f"{split}.csv")
        out = STAGE / "data" / "processed"
        (out / "audio" / split).mkdir(parents=True, exist_ok=True)
        df.to_csv(out / f"{split}.csv", index=False, encoding="utf-8")
        for a in df["audio"]:
            shutil.copy(ROOT / a, STAGE / a)

    # Bake the model id into the image
    docker = (STAGE / "Dockerfile").read_text(encoding="utf-8")
    (STAGE / "Dockerfile").write_text(docker.replace("ARG TWIBENCH_MODEL", f"ARG TWIBENCH_MODEL={model_id}"),
                                      encoding="utf-8")
    size = sum(p.stat().st_size for p in STAGE.rglob("*") if p.is_file()) / 1e6
    print(f"Staged app in {STAGE} ({size:.0f} MB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True, help="your Hugging Face username")
    ap.add_argument("--space", default="twibench")
    ap.add_argument("--model-repo", default="whisper-small-twi")
    ap.add_argument("--dry-run", action="store_true", help="stage files only, upload nothing")
    ap.add_argument("--app-only", action="store_true", help="don't (re)upload the model")
    args = ap.parse_args()

    model_id = f"{args.user}/{args.model_repo}"
    space_id = f"{args.user}/{args.space}"
    stage(model_id)
    if args.dry_run:
        print("Dry run: nothing uploaded.")
        return

    from huggingface_hub import HfApi
    api = HfApi()
    print("Logged in as", api.whoami()["name"])

    if not args.app_only:
        m = pd.read_csv(ROOT / "results" / "metrics.csv").set_index(["model", "split"])
        card = MODEL_CARD.format(zs=m.loc[("whisper-small", "test"), "wer"],
                                 ft=m.loc[("whisper-small-ft", "test"), "wer"],
                                 ft_cer=m.loc[("whisper-small-ft", "test"), "cer"])
        model_dir = ROOT / "models" / "whisper-small-twi"
        (model_dir / "README.md").write_text(card, encoding="utf-8")
        api.create_repo(model_id, repo_type="model", exist_ok=True)
        print(f"Uploading model to {model_id} (~930 MB, resumes if interrupted)...")
        api.upload_folder(repo_id=model_id, folder_path=model_dir, repo_type="model",
                          ignore_patterns=["training_args.bin", "training_log.csv", "checkpoint-*"])

    api.create_repo(space_id, repo_type="space", space_sdk="docker", exist_ok=True)
    print(f"Uploading app to {space_id}...")
    api.upload_folder(repo_id=space_id, folder_path=STAGE, repo_type="space")
    print(f"\nDone. Your site builds in ~5-10 minutes at: https://huggingface.co/spaces/{space_id}")


if __name__ == "__main__":
    main()
