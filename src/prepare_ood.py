"""Out-of-domain test set: scripture-style read Twi (d3vnerd/twi_dataset, MIT).

Used only for testing, to check whether models generalise beyond the
financial domain of the training data.

Usage:
    python src/prepare_ood.py
Outputs:
    data/processed/ood_test.csv
    data/processed/audio/ood_test/*.flac
"""
import io
from pathlib import Path

import librosa
import pandas as pd
import pyarrow.parquet as pq
import soundfile as sf
from huggingface_hub import HfApi, hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
REPO = "d3vnerd/twi_dataset"
SR = 16_000
# CPU budget: evaluate on a fixed random sample (the full list is kept in ood_test_full.csv).
OOD_CLIPS = 150


def sample(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(n=min(OOD_CLIPS, len(df)), random_state=42).sort_index()


def main():
    files = [f for f in HfApi().list_repo_files(REPO, repo_type="dataset")
             if f.endswith(".parquet") and "test" in Path(f).name]
    out_dir = ROOT / "data" / "processed" / "audio" / "ood_test"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for f in files:
        local = Path(hf_hub_download(REPO, f, repo_type="dataset", local_dir=ROOT / "data" / "raw" / "tmp_ood"))
        with open(local, "rb") as fh:
            table = pq.ParquetFile(fh).read()
        audio_col = "audio" if "audio" in table.column_names else table.column_names[0]
        for i, (a, text) in enumerate(zip(table.column(audio_col).to_pylist(),
                                          table.column("transcription").to_pylist())):
            y, sr = sf.read(io.BytesIO(a["bytes"]), dtype="float32")
            if y.ndim > 1:
                y = y.mean(axis=1)
            if sr != SR:
                y = librosa.resample(y, orig_sr=sr, target_sr=SR)
            rel = Path("data/processed/audio/ood_test") / f"{Path(f).stem}_{i:05d}.flac"
            sf.write(ROOT / rel, y, SR)
            rows.append({"audio": rel.as_posix(), "text": text, "duration": round(len(y) / SR, 3)})
        local.unlink()

    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "data" / "processed" / "ood_test_full.csv", index=False, encoding="utf-8")
    sub = sample(df)
    sub.to_csv(ROOT / "data" / "processed" / "ood_test.csv", index=False, encoding="utf-8")
    print(f"{len(df)} clips ({df['duration'].sum() / 3600:.2f} h); "
          f"evaluation sample {len(sub)} clips ({sub['duration'].sum() / 3600:.2f} h)")


if __name__ == "__main__":
    main()
