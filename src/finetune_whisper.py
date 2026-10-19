"""Step 7: fine-tune Whisper-small on the TwiBench train split. Needs a GPU
(run it on Kaggle/Colab via notebooks/twibench_kaggle.ipynb).

The train/dev split is computed from the file names with the same hash as
prepare_data.py, so it always matches the local test set.

Usage (GPU, full train split):
    python src/finetune_whisper.py --output models/whisper-small-twi
Usage (CPU, local train sample, decoder only):
    python src/finetune_whisper.py --data local --freeze-encoder --batch-size 8 --grad-accum 1 \
        --max-steps 2000 --dev-clips 150 --eval-steps 500 --lr 3e-5
"""
import argparse
import io
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import jiwer
import librosa
import pandas as pd
import soundfile as sf
import torch
from datasets import Audio, Dataset, concatenate_datasets, load_dataset
from transformers import (Seq2SeqTrainer, Seq2SeqTrainingArguments, TrainerCallback,
                          WhisperForConditionalGeneration, WhisperProcessor)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import normalize  # noqa: E402
from prepare_data import NAME_RE, SOURCES, bucket  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SR = 16_000


def split_of(file_name: str, dialect: str) -> str:
    m = NAME_RE.match(file_name)
    if not m:
        return "unused"
    s, p = bucket(f"{dialect}:{m['speaker']}"), bucket(m["prompt"])
    return s if s == p else "unused"


def load_splits(dev_clips: int):
    parts = []
    for dialect, repo in SOURCES.items():
        ds = load_dataset(repo)
        ds = concatenate_datasets([ds[s] for s in ds])          # we re-split ourselves
        ds = ds.cast_column("audio_path", Audio(decode=False))  # decoded in the collator
        ds = ds.map(lambda b: {"split": [split_of(a["path"], dialect) for a in b["audio_path"]]},
                    batched=True, num_proc=4)
        parts.append(ds)
    ds = concatenate_datasets(parts)
    train = ds.filter(lambda s: s == "train", input_columns="split", num_proc=4)
    dev = ds.filter(lambda s: s == "dev", input_columns="split", num_proc=4)
    dev = dev.shuffle(seed=0).select(range(min(dev_clips, len(dev))))
    print(f"train {len(train)} clips | dev subset {len(dev)} clips")
    return train, dev


def load_local_splits(dev_clips: int):
    """CPU mode: the train sample and dev clips exported by prepare_data.py."""
    def read(split):
        df = pd.read_csv(ROOT / "data" / "processed" / f"{split}.csv")
        return Dataset.from_pandas(df[["audio", "text"]].rename(columns={"text": "transcription"}),
                                   preserve_index=False)
    train, dev = read("train"), read("dev")
    dev = dev.shuffle(seed=0).select(range(min(dev_clips, len(dev))))
    print(f"train {len(train)} clips | dev subset {len(dev)} clips (local)")
    return train, dev


def load_audio(row):
    if "audio_path" not in row:  # local FLAC, already 16 kHz mono
        return sf.read(ROOT / row["audio"], dtype="float32")[0]
    y, sr = sf.read(io.BytesIO(row["audio_path"]["bytes"]), dtype="float32")
    if y.ndim > 1:
        y = y.mean(axis=1)
    return y if sr == SR else librosa.resample(y, orig_sr=sr, target_sr=SR)


@dataclass
class Collator:
    """Decodes audio and builds log-mel features on the fly (no feature cache on disk)."""
    processor: WhisperProcessor

    def __call__(self, rows):
        audio = [load_audio(r) for r in rows]
        batch = self.processor.feature_extractor(audio, sampling_rate=SR, return_tensors="pt")
        labels = self.processor.tokenizer([r["transcription"].strip() for r in rows],
                                          padding=True, return_tensors="pt")
        ids = labels["input_ids"].masked_fill(labels.attention_mask.ne(1), -100)
        sot = self.processor.tokenizer.convert_tokens_to_ids("<|startoftranscript|>")
        if (ids[:, 0] == sot).all():  # the model adds it back as decoder start token
            ids = ids[:, 1:]
        batch["labels"] = ids
        return batch


class TimeBudget(TrainerCallback):
    """Stop training cleanly once a wall-clock budget is used up."""

    def __init__(self, hours: float):
        self.deadline = time.time() + hours * 3600

    def on_step_end(self, args, state, control, **kwargs):
        if time.time() > self.deadline:
            print(f"Time budget reached at step {state.global_step}; stopping.", flush=True)
            control.should_training_stop = True
        return control


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-model", default="openai/whisper-small")
    ap.add_argument("--output", default="models/whisper-small-twi")
    ap.add_argument("--language", default="yoruba",
                    help="proxy language token (Twi is not a Whisper language); use the same one at evaluation")
    ap.add_argument("--max-steps", type=int, default=4000)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--dev-clips", type=int, default=600)
    ap.add_argument("--eval-steps", type=int, default=500)
    ap.add_argument("--data", choices=["hf", "local"], default="hf",
                    help="hf: full train split streamed from Hugging Face (GPU); "
                         "local: the train sample exported by prepare_data.py (CPU)")
    ap.add_argument("--freeze-encoder", action="store_true",
                    help="train the decoder only (much faster; used for CPU runs)")
    ap.add_argument("--warmup-steps", type=int, help="default: min(400, max_steps / 10)")
    ap.add_argument("--max-hours", type=float,
                    help="stop training after this many hours (uses a constant LR so stopping early is clean)")
    args = ap.parse_args()
    gpu = torch.cuda.is_available()

    processor = WhisperProcessor.from_pretrained(args.base_model, language=args.language, task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(args.base_model)
    model.generation_config.language = args.language
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    model.config.use_cache = False
    if args.freeze_encoder:
        model.freeze_encoder()
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"trainable parameters: {n_train / 1e6:.0f}M | device: {'cuda' if gpu else 'cpu'}")

    train, dev = load_splits(args.dev_clips) if args.data == "hf" else load_local_splits(args.dev_clips)

    def compute_metrics(pred):
        ids = pred.label_ids.copy()
        ids[ids == -100] = processor.tokenizer.pad_token_id
        hyp = [normalize(t) for t in processor.batch_decode(pred.predictions, skip_special_tokens=True)]
        ref = [normalize(t) for t in processor.batch_decode(ids, skip_special_tokens=True)]
        return {"wer": jiwer.wer(ref, hyp), "cer": jiwer.cer(ref, hyp)}

    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        per_device_eval_batch_size=16,
        learning_rate=args.lr,
        warmup_steps=args.warmup_steps if args.warmup_steps is not None else min(400, args.max_steps // 10),
        lr_scheduler_type="constant_with_warmup" if args.max_hours else "linear",
        max_steps=args.max_steps,
        fp16=gpu,
        gradient_checkpointing=gpu and not args.freeze_encoder,
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        # On a small local disk, skip ~1-2 GB checkpoints and keep only the final model.
        save_strategy="steps" if gpu else "no",
        save_steps=args.eval_steps,
        save_total_limit=2,
        logging_steps=50 if gpu else 10,
        predict_with_generate=True,
        generation_max_length=128,
        load_best_model_at_end=gpu,
        metric_for_best_model="wer",
        greater_is_better=False,
        report_to="none",
        dataloader_num_workers=4 if gpu else 0,
        remove_unused_columns=False,  # the collator needs the raw audio + text columns
        seed=42,
    )
    trainer = Seq2SeqTrainer(
        model=model, args=training_args,
        train_dataset=train, eval_dataset=dev,
        data_collator=Collator(processor),
        compute_metrics=compute_metrics,
        processing_class=processor,
        callbacks=[TimeBudget(args.max_hours)] if args.max_hours else None,
    )
    trainer.train()

    model.config.use_cache = True
    trainer.save_model(args.output)
    processor.save_pretrained(args.output)
    pd.DataFrame(trainer.state.log_history).to_csv(Path(args.output) / "training_log.csv", index=False)
    print("Best dev result:", trainer.evaluate())


if __name__ == "__main__":
    main()
