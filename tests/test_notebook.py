"""The Kaggle notebook embeds src/*.py; it must be rebuilt after src changes,
and fine-tuning must use exactly the same split as prepare_data.py."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "notebooks"))
from build_notebook import SRC_FILES  # noqa: E402


def test_notebook_embeds_current_src():
    nb = json.loads((ROOT / "notebooks" / "twibench.ipynb").read_text(encoding="utf-8"))
    embedded = {}
    for c in nb["cells"]:
        src = "".join(c["source"])
        if src.startswith("%%writefile src/"):
            name, body = src.split("\n", 1)
            embedded[name.removeprefix("%%writefile src/")] = body
    for name in SRC_FILES:
        current = (ROOT / "src" / name).read_text(encoding="utf-8")
        assert embedded.get(name) == current, f"{name} changed: run python notebooks/build_notebook.py"


def test_finetune_split_matches_prepare_data():
    import prepare_data
    from finetune_whisper import split_of

    names = [f"AsantiTwi{g}{a}-SPK{i:04d}-Tmp{p:03d}-x.wav"
             for i in range(300) for p in range(0, 130, 7) for g, a in [("Fm", 20), ("Ma", 31)][i % 2:i % 2 + 1]]
    df = prepare_data.parse(pd.DataFrame({"file": names, "text": "x"}), "asante")
    assert list(df["split"]) == [split_of(n, "asante") for n in names]
    assert {"train", "dev", "test", "unused"} <= set(df["split"])
