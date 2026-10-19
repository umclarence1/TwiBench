"""Steps 5/6/9: run an ASR model on a test manifest and score it.

Examples:
    python src/evaluate.py --model whisper-small --limit 20      # quick check
    python src/evaluate.py --model whisper-small
    python src/evaluate.py --model mms
    python src/evaluate.py --model <hf-id-or-folder> --kind whisper --tag whisper-small-ft --language yoruba
    python src/evaluate.py --model mms --split ood_test

Outputs:
    results/predictions/<tag>__<split>.csv   one row per clip (ref, pred, per-clip WER/CER)
    results/metrics.csv                      one row per (model, split); re-runs replace the row
"""
import argparse
import sys
import time
from pathlib import Path

import jiwer
import librosa
import pandas as pd
import torch
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import normalize  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SR = 16_000
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

PRESETS = {
    "whisper-small": dict(model="openai/whisper-small", kind="whisper"),
    "mms": dict(model="facebook/mms-1b-all", kind="mms"),
    "akan-whisper": dict(model="GiftMark/akan-whisper-model", kind="whisper"),
}


class WhisperASR:
    def __init__(self, model_id, language=None):
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
        self.processor = WhisperProcessor.from_pretrained(model_id)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_id).to(DEVICE).eval()
        # Twi is not a Whisper language: zero-shot uses auto-detection unless
        # a language is given; fine-tuned models use the proxy language they were trained with.
        self.gen = dict(task="transcribe", max_new_tokens=128)
        if language:
            self.gen["language"] = language

    @torch.inference_mode()
    def __call__(self, batch):
        feats = self.processor(batch, sampling_rate=SR, return_tensors="pt").input_features.to(DEVICE)
        ids = self.model.generate(feats, **self.gen)
        return self.processor.batch_decode(ids, skip_special_tokens=True)


class MmsASR:
    def __init__(self, model_id, lang="aka"):
        from transformers import AutoProcessor, Wav2Vec2ForCTC
        self.processor = AutoProcessor.from_pretrained(model_id, target_lang=lang)
        self.model = Wav2Vec2ForCTC.from_pretrained(
            model_id, target_lang=lang, ignore_mismatched_sizes=True).to(DEVICE).eval()

    @torch.inference_mode()
    def __call__(self, batch):
        inputs = self.processor(batch, sampling_rate=SR, return_tensors="pt", padding=True).to(DEVICE)
        logits = self.model(**inputs).logits
        return self.processor.batch_decode(logits.argmax(dim=-1).cpu())


def score(refs, hyps, fold=False):
    r = [normalize(x, fold) for x in refs]
    h = [normalize(x, fold) for x in hyps]
    return jiwer.wer(r, h), jiwer.cer(r, h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="preset name, HF id, or local folder")
    ap.add_argument("--kind", choices=["whisper", "mms"], help="needed when --model is not a preset")
    ap.add_argument("--tag", help="name used in results (default: preset name / folder name)")
    ap.add_argument("--split", default="test", help="manifest in data/processed/<split>.csv")
    ap.add_argument("--language", help="Whisper language token (fine-tuned models)")
    ap.add_argument("--mms-lang", default="aka")
    ap.add_argument("--limit", type=int, help="evaluate only the first N clips (smoke test)")
    ap.add_argument("--batch-size", type=int, default=8)
    args = ap.parse_args()

    preset = PRESETS.get(args.model, {})
    model_id = preset.get("model", args.model)
    kind = args.kind or preset.get("kind")
    if not kind:
        ap.error("--kind is required for a non-preset model")
    tag = args.tag or (args.model if preset else Path(args.model).name)

    df = pd.read_csv(ROOT / "data" / "processed" / f"{args.split}.csv")
    if args.limit:
        df = df.head(args.limit)
    print(f"{tag}: {len(df)} clips from {args.split} on {DEVICE}")

    asr = WhisperASR(model_id, args.language) if kind == "whisper" else MmsASR(model_id, args.mms_lang)

    preds, t0 = [], time.time()
    for i in tqdm(range(0, len(df), args.batch_size)):
        paths = df["audio"].iloc[i:i + args.batch_size]
        audio = [librosa.load(ROOT / p, sr=SR)[0] for p in paths]
        preds.extend(asr(audio))
    elapsed = time.time() - t0

    df["pred"] = [p.strip() for p in preds]
    df["ref_norm"] = df["text"].map(normalize)
    df["pred_norm"] = df["pred"].map(normalize)
    df["wer"] = [jiwer.wer(r, h) if r else None for r, h in zip(df["ref_norm"], df["pred_norm"])]
    df["cer"] = [jiwer.cer(r, h) if r else None for r, h in zip(df["ref_norm"], df["pred_norm"])]

    out = ROOT / "results" / "predictions"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / f"{tag}__{args.split}.csv", index=False, encoding="utf-8")

    wer, cer = score(df["text"], df["pred"])
    wer_f, cer_f = score(df["text"], df["pred"], fold=True)
    row = {"model": tag, "model_id": model_id, "split": args.split, "clips": len(df),
           "wer": wer, "cer": cer, "wer_folded": wer_f, "cer_folded": cer_f}
    for col in ["dialect", "gender"]:
        if col in df:
            for val, g in df.groupby(col):
                row[f"wer_{val}"], row[f"cer_{val}"] = score(g["text"], g["pred"])
    audio_secs = df["duration"].sum() if "duration" in df else None
    row["real_time_factor"] = elapsed / audio_secs if audio_secs else None
    row = {k: round(v, 4) if isinstance(v, float) else v for k, v in row.items()}

    metrics = ROOT / "results" / "metrics.csv"
    old = pd.read_csv(metrics) if metrics.exists() else pd.DataFrame()
    if not old.empty and not args.limit:
        old = old[~((old["model"] == tag) & (old["split"] == args.split))]
    if not args.limit:  # smoke tests are not recorded
        pd.concat([old, pd.DataFrame([row])], ignore_index=True).to_csv(metrics, index=False)

    print(pd.Series(row).to_string())
    print("\nExamples:")
    for _, r in df.head(5).iterrows():
        print(f"  REF:  {r['text']}\n  PRED: {r['pred']}\n")


if __name__ == "__main__":
    main()
