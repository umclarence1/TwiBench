"""Steps 2-3: download the Ashesi Twi data, build a speaker- and
sentence-disjoint train/dev/test split, and export dev/test audio locally.

Source: Ashesi Financial Inclusion Speech Dataset (CC-BY-4.0), via the
Hugging Face mirrors below. Original file names encode the metadata, e.g.
    AsantiTwiFm18-MHdyb4ij-Tmp002-YvH2jV.wav
    <dialect><gender><age>-<speaker_id>-<prompt_id>-<clip_id>

Split rule: a speaker and a prompt (sentence) are each hashed into
train/dev/test; a clip is kept only if both land in the same split, so no
test speaker and no test sentence is ever seen in training. Hashing makes
the split deterministic and lets us process one shard at a time.

To save disk space each shard (~450 MB) is downloaded, processed and
deleted. Kept locally (16 kHz FLAC): all dev/test audio plus a fixed ~36%
sample of train audio for CPU fine-tuning.

Usage:
    python src/prepare_data.py
Outputs:
    data/processed/metadata.csv        every clip, parsed fields + split
    data/processed/{train,dev,test}.csv      manifests with local audio paths
    data/processed/audio/{train,dev,test}/   16 kHz FLAC files
    results/data_stats.csv             clips / hours / speakers / prompts
"""
import hashlib
import io
import re
import shutil
import time
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import soundfile as sf
from huggingface_hub import HfApi, hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
TMP = ROOT / "data" / "raw" / "tmp"
SR = 16_000

# Fraction of speakers AND of prompts assigned to each evaluation split.
DEV_FRAC = 0.10
TEST_FRAC = 0.15
SALT = "twibench-v1"  # change only if you deliberately want a new split
# Share of train clips whose audio is kept locally (~12k clips) for CPU
# fine-tuning; the GPU notebook reads all train audio from Hugging Face instead.
TRAIN_EXPORT_FRAC = 0.36
MIN_FREE_GB = 1.5  # never fill the disk: stop (resumably) below this
# Shards used per dialect (sorted order: test shard first, then train shards).
# Limited to save internet data: currently Asante only (3 shards).
# Set to None to use every shard of both dialects.
MAX_SHARDS = {"asante": 3, "akuapem": 0}

SOURCES = {
    "asante": "ghanaopenai/twi_multispeaker_audio_transcribed",
    "akuapem": "ghanaopenai/akuapem_multispeaker_audio_transcribed",
}

NAME_RE = re.compile(
    r"^(?P<lang>AsantiTwi|AkuapemTwi)(?P<gender>Fm|Ma|F|M)(?P<age>\d+)"
    r"-(?P<speaker>[^-]+)-(?P<prompt>Tmp\d+)-(?P<clip>[^.]+)\."
)


def unit_hash(key: str) -> float:
    """Deterministic pseudo-random number in [0, 1] for a key."""
    return int(hashlib.sha1(f"{SALT}:{key}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def bucket(key: str) -> str:
    """Deterministically map a speaker or prompt ID to train/dev/test."""
    h = unit_hash(key)
    if h < TEST_FRAC:
        return "test"
    if h < TEST_FRAC + DEV_FRAC:
        return "dev"
    return "train"


def download(repo: str, filename: str, retries: int = 10) -> Path:
    """Download one file, resuming after network drops."""
    for attempt in range(1, retries + 1):
        try:
            return Path(hf_hub_download(repo, filename, repo_type="dataset", local_dir=TMP))
        except Exception as e:
            wait = min(60, 5 * attempt)
            print(f"  download failed ({type(e).__name__}), retry {attempt}/{retries} in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"Could not download {repo}/{filename}")


def parse(df: pd.DataFrame, dialect: str) -> pd.DataFrame:
    parsed = df["file"].str.extract(NAME_RE)
    bad = parsed["speaker"].isna()
    if bad.any():
        print(f"  WARNING: {bad.sum()} unparsed names dropped, e.g. {df.loc[bad, 'file'].head(2).tolist()}")
    df = pd.concat([df, parsed.drop(columns="lang")], axis=1)[~bad].copy()
    df["gender"] = df["gender"].str[0].map({"F": "female", "M": "male"})
    df["age"] = df["age"].astype(int)
    df["speaker"] = dialect + ":" + df["speaker"]
    s, p = df["speaker"].map(bucket), df["prompt"].map(bucket)
    df["split"] = np.where(s == p, s, "unused")
    return df


def process_shard(repo: str, file: str, dialect: str) -> pd.DataFrame:
    local = download(repo, file)
    with open(local, "rb") as fh:
        df = read_shard(pq.ParquetFile(fh), repo, file, dialect)
    local.unlink()  # free disk space (file must be closed first on Windows)
    return df


def read_shard(pf: pq.ParquetFile, repo: str, file: str, dialect: str) -> pd.DataFrame:
    meta = pf.read(columns=["audio_path.path", "transcription"])
    df = pd.DataFrame({
        "file": [r["path"] for r in meta.column("audio_path").to_pylist()],
        "text": meta.column("transcription").to_pylist(),
    })
    df["dialect"], df["hf_repo"], df["hf_file"], df["hf_row"] = dialect, repo, file, np.arange(len(df))
    df = parse(df, dialect)
    df["duration"] = np.nan
    df["audio"] = ""

    # Export dev/test audio and a fixed sample of train audio (for CPU
    # fine-tuning), row group by row group to keep memory low.
    train_sample = (df["split"] == "train") & (df["file"].map(lambda f: unit_hash("clip:" + f)) < TRAIN_EXPORT_FRAC)
    keep = set(df.index[df["split"].isin(["dev", "test"]) | train_sample])
    offset = 0
    for rg in range(pf.metadata.num_row_groups):
        table = pf.read_row_group(rg, columns=["audio_path"])
        n = table.num_rows
        audio = table.column("audio_path").to_pylist()
        for i in range(offset, offset + n):
            if i in df.index:
                df.at[i, "duration"] = round(sf.info(io.BytesIO(audio[i - offset]["bytes"])).duration, 3)
        wanted = [i for i in range(offset, offset + n) if i in keep]
        if wanted:
            for i in wanted:
                y, sr = sf.read(io.BytesIO(audio[i - offset]["bytes"]), dtype="float32")
                if y.ndim > 1:
                    y = y.mean(axis=1)
                if sr != SR:
                    y = librosa.resample(y, orig_sr=sr, target_sr=SR)
                split = df.at[i, "split"]
                rel = Path("data/processed/audio") / split / (Path(df.at[i, "file"]).stem + ".flac")
                (ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
                sf.write(ROOT / rel, y, SR)
                df.at[i, "audio"] = rel.as_posix()
                df.at[i, "duration"] = round(len(y) / SR, 3)
        offset += n
    return df


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / "results").mkdir(exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)

    # Resume support: shards already processed are cached as small CSVs.
    done_dir = OUT / "shards"
    done_dir.mkdir(exist_ok=True)

    frames = []
    for dialect, repo in SOURCES.items():
        files = sorted(f for f in HfApi().list_repo_files(repo, repo_type="dataset") if f.endswith(".parquet"))
        files = files[:MAX_SHARDS[dialect]] if MAX_SHARDS else files
        for file in files:
            cache = done_dir / f"{dialect}_{Path(file).stem}.csv"
            if cache.exists():
                print("cached ", dialect, file, flush=True)
                frames.append(pd.read_csv(cache))
                continue
            free_gb = shutil.disk_usage(ROOT).free / 1e9
            if free_gb < MIN_FREE_GB:
                raise SystemExit(f"Stopping: only {free_gb:.1f} GB free on disk (need {MIN_FREE_GB} GB). "
                                 "Free some space and re-run; finished shards are skipped.")
            print(f"process {dialect} {file}  ({free_gb:.1f} GB free)", flush=True)
            df = process_shard(repo, file, dialect)
            df.to_csv(cache, index=False, encoding="utf-8")
            frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    dups = df.duplicated(["dialect", "file"]).sum()
    if dups:
        print(f"Dropping {dups} duplicate files")
        df = df.drop_duplicates(["dialect", "file"])

    df.to_csv(OUT / "metadata.csv", index=False, encoding="utf-8")
    cols = ["audio", "text", "dialect", "gender", "age", "speaker", "prompt", "duration", "file"]
    for split in ["dev", "test"]:
        df[df["split"] == split][cols].to_csv(OUT / f"{split}.csv", index=False, encoding="utf-8")
    exported_train = df[(df["split"] == "train") & df["audio"].fillna("").ne("")]
    exported_train[cols].to_csv(OUT / "train.csv", index=False, encoding="utf-8")

    st = (df.groupby(["split", "dialect"])
            .agg(clips=("file", "size"), speakers=("speaker", "nunique"),
                 prompts=("prompt", "nunique"), hours=("duration", lambda d: round(d.sum() / 3600, 2)),
                 female_share=("gender", lambda g: round((g == "female").mean(), 2)))
            .reset_index())
    st.to_csv(ROOT / "results" / "data_stats.csv", index=False)
    print(st.to_string(index=False))
    print("\nTotal clips:", len(df), "| speakers:", df["speaker"].nunique(), "| prompts:", df["prompt"].nunique())

    # Leakage check: no test/dev speaker or prompt may appear in train.
    tr = df[df["split"] == "train"]
    for split in ["dev", "test"]:
        ev = df[df["split"] == split]
        assert not set(ev["speaker"]) & set(tr["speaker"]), f"speaker leak in {split}"
        assert not set(ev["prompt"]) & set(tr["prompt"]), f"prompt leak in {split}"
    print("Leakage check passed: dev/test speakers and prompts are unseen in train.")


if __name__ == "__main__":
    main()
