"""Step 10: error analysis of saved predictions (results/predictions/*.csv).

For each prediction file it counts the error types from the plan, using the
word alignment between normalised reference and hypothesis:
    vowel     ɛ/ɔ-only substitutions (word is right once ɛ->e, ɔ->o are folded)
    boundary  words wrongly joined or split ("melki ba" -> "melkiba")
    loanword  errors on English / code-switched words (credit, cedis, network...)
    number    errors on tokens containing digits
    other     remaining substitutions, deletions, insertions
plus hallucinated outputs (runaway repetition or far longer than the reference).

Usage:
    python src/error_analysis.py
Outputs (results/error_analysis/):
    summary.csv              one row per model x split: error-type shares, hallucination rate
    confusions_<tag>.csv     most frequent word substitutions / deletions / insertions
    examples_<tag>.md        worst and typical examples for the report
    fig_wer_cer.png          WER and CER by model and test set
    fig_error_types.png      error-type breakdown by model (in-domain test)
    fig_dialect.png          WER by dialect
"""
import re
import sys
from collections import Counter
from pathlib import Path

import jiwer
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import normalize  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRED_DIR = ROOT / "results" / "predictions"
OUT = ROOT / "results" / "error_analysis"

# Twi orthography does not use these letters, so words containing them are
# loans; plus common English words in the financial-domain prompts.
LOAN_LETTERS = set("cjqvxz")
LOAN_WORDS = {
    "network", "transfer", "credit", "cedi", "cedis", "momo", "account", "bank", "mobile", "money",
    "pin", "number", "balance", "airtime", "data", "bundle", "sim", "card", "phone", "send", "ok",
    "sms", "code", "agent", "wallet", "loan", "pesewas", "mtn", "vodafone", "airteltigo", "kyc",
}
FOLD = str.maketrans({"ɛ": "e", "ɔ": "o"})

# Figure styling (validated reference palette: slot 1 blue, slot 2 orange)
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]
TYPE_ORDER = ["vowel", "boundary", "loanword", "number", "other"]
# Fixed model order -> fixed colour, so a model keeps its colour in every figure.
MODEL_ORDER = ["whisper-small", "whisper-small-ft", "akan-whisper", "mms"]
MODEL_LABELS = {"whisper-small": "Whisper-small (zero-shot)",
                "whisper-small-ft": "Whisper-small (fine-tuned)",
                "akan-whisper": "Community Akan Whisper", "mms": "MMS (aka)"}


def ordered(models):
    models = list(dict.fromkeys(models))
    return sorted(models, key=lambda m: (MODEL_ORDER.index(m) if m in MODEL_ORDER else 99, m))


def is_loan(w: str) -> bool:
    return w in LOAN_WORDS or bool(set(w) & LOAN_LETTERS)


def is_hallucination(ref: str, hyp: str) -> bool:
    r, h = ref.split(), hyp.split()
    if re.search(r"(.)\1{7,}", hyp):  # same character 8+ times
        return True
    if len(h) >= 4 and Counter(h).most_common(1)[0][1] >= max(4, len(h) // 2):
        return True  # one word repeated in a loop
    return len(h) > 2 * len(r) + 3


def boundary_words(r: list, h: list) -> tuple[set, set]:
    """Indices of ref/hyp words involved in a join ("melki ba" -> "melkiba")
    or a split ("nkɔmmɔ" -> "nkɔ mmɔ")."""
    ref_idx, hyp_idx = set(), set()
    rset, hset = set(r), set(h)
    joins = {r[i] + r[i + 1]: i for i in range(len(r) - 1)}
    for j, w in enumerate(h):
        if w not in rset and w in joins:
            ref_idx |= {joins[w], joins[w] + 1}
            hyp_idx.add(j)
    splits = {h[j] + h[j + 1]: j for j in range(len(h) - 1)}
    for i, w in enumerate(r):
        if w not in hset and w in splits:
            ref_idx.add(i)
            hyp_idx |= {splits[w], splits[w] + 1}
    return ref_idx, hyp_idx


def classify(ref: str, hyp: str) -> Counter:
    """Word errors by type for one utterance, in the same units as WER
    (each substitution, deletion and insertion is counted exactly once)."""
    c = Counter()
    if not ref:
        return c
    out = jiwer.process_words(ref, hyp)
    rw, hw = out.references[0], out.hypotheses[0]
    b_ref, b_hyp = boundary_words(rw, hw)

    def ref_type(x):
        return "number" if any(ch.isdigit() for ch in x) else "loanword" if is_loan(x) else "other"

    for a in out.alignments[0]:
        if a.type == "equal":
            continue
        ri = range(a.ref_start_idx, a.ref_end_idx)
        hi = range(a.hyp_start_idx, a.hyp_end_idx)
        if a.type == "substitute":
            for i, j in zip(ri, hi):
                x, y = rw[i], hw[j]
                if i in b_ref or j in b_hyp:
                    c["boundary"] += 1
                elif x.translate(FOLD) == y.translate(FOLD):
                    c["vowel"] += 1
                else:
                    c[ref_type(x)] += 1
        elif a.type == "delete":
            for i in ri:
                c["boundary" if i in b_ref else ref_type(rw[i])] += 1
        else:  # insert
            for j in hi:
                c["boundary" if j in b_hyp else "other"] += 1
    return c


def analyse(path: Path) -> tuple[dict, pd.DataFrame]:
    tag, split = path.stem.split("__")
    df = pd.read_csv(path).fillna({"pred": "", "ref_norm": "", "pred_norm": ""})
    df["ref_norm"] = df["text"].map(normalize)
    df["pred_norm"] = df["pred"].map(normalize)

    totals, confusions = Counter(), Counter()
    df["hallucination"] = [is_hallucination(r, h) for r, h in zip(df["ref_norm"], df["pred_norm"])]
    for r, h in zip(df["ref_norm"], df["pred_norm"]):
        totals.update(classify(r, h))
        out = jiwer.process_words(r or "-", h)
        rw, hw = out.references[0], out.hypotheses[0]
        for a in out.alignments[0]:
            if a.type == "substitute":
                for x, y in zip(rw[a.ref_start_idx:a.ref_end_idx], hw[a.hyp_start_idx:a.hyp_end_idx]):
                    confusions[("sub", x, y)] += 1
            elif a.type == "delete":
                for x in rw[a.ref_start_idx:a.ref_end_idx]:
                    confusions[("del", x, "")] += 1
            elif a.type == "insert":
                for y in hw[a.hyp_start_idx:a.hyp_end_idx]:
                    confusions[("ins", "", y)] += 1

    n_err = sum(totals.values()) or 1
    ok = df["ref_norm"] != ""
    row = {"model": tag, "split": split, "clips": len(df),
           "wer": jiwer.wer(list(df.loc[ok, "ref_norm"]), list(df.loc[ok, "pred_norm"])),
           "cer": jiwer.cer(list(df.loc[ok, "ref_norm"]), list(df.loc[ok, "pred_norm"])),
           "hallucination_rate": df["hallucination"].mean(),
           "errors_counted": sum(totals.values())}
    row.update({f"share_{t}": totals[t] / n_err for t in TYPE_ORDER})

    # Loanword vs native-word accuracy
    loan_ref = sum(is_loan(w) for r in df["ref_norm"] for w in r.split())
    row["loanword_tokens"] = loan_ref

    conf = pd.DataFrame([{"type": k[0], "ref": k[1], "hyp": k[2], "count": v}
                         for k, v in confusions.most_common(60)])
    OUT.mkdir(parents=True, exist_ok=True)
    conf.to_csv(OUT / f"confusions_{tag}__{split}.csv", index=False, encoding="utf-8")
    write_examples(df, tag, split)
    return row, df


def write_examples(df: pd.DataFrame, tag: str, split: str):
    d = df[df["ref_norm"] != ""].copy()
    lines = [f"# Examples: {tag} on {split}\n"]
    sections = [
        ("Hallucinations", d[d["hallucination"]].head(5)),
        ("Highest WER (excluding hallucinations)", d[~d["hallucination"]].nlargest(5, "wer")),
        ("Typical errors (WER near the median)",
         d.iloc[(d["wer"] - d["wer"].median()).abs().argsort()[:5]]),
        ("Perfect transcriptions", d[d["wer"] == 0].head(5)),
    ]
    for title, rows in sections:
        lines.append(f"\n## {title}\n")
        if rows.empty:
            lines.append("_none_\n")
        for _, r in rows.iterrows():
            extra = f" · {r['dialect']}" if "dialect" in r and pd.notna(r.get("dialect")) else ""
            lines.append(f"- **REF:** {r['text']}  \n  **HYP:** {str(r['pred'])[:200]}  \n"
                         f"  WER {r['wer']:.2f}{extra}\n")
    (OUT / f"examples_{tag}__{split}.md").write_text("\n".join(lines), encoding="utf-8")


def style(ax, title):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", color=INK, fontsize=12, pad=28)  # room for the legend row
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def bars(ax, groups, series, values, fmt="{:.0%}"):
    """Grouped bars with direct value labels. values[s][g]."""
    n = len(series)
    width = 0.8 / n
    top = 0
    for i, s in enumerate(series):
        xs = [g + (i - (n - 1) / 2) * width for g in range(len(groups))]
        ys = [values[s].get(g, float("nan")) for g in groups]
        colour = SERIES[MODEL_ORDER.index(s) % len(SERIES)] if s in MODEL_ORDER else SERIES[i % len(SERIES)]
        b = ax.bar(xs, ys, width * 0.92, color=colour, label=MODEL_LABELS.get(s, s),
                   edgecolor=SURFACE, linewidth=1)
        ax.bar_label(b, labels=["" if pd.isna(y) else fmt.format(y) for y in ys], color=INK, fontsize=8, padding=2)
        top = max([top] + [y for y in ys if not pd.isna(y)])
    ax.set_ylim(0, (top or 1) * 1.15)  # headroom for value labels
    ax.set_xticks(range(len(groups)), groups, color=INK)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.legend(frameon=False, labelcolor=INK_2, fontsize=9, ncol=n,
              loc="lower left", bbox_to_anchor=(0, 1.0), borderaxespad=0.2)


def figures(summary: pd.DataFrame, frames: dict):
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": SURFACE})
    models = ordered(summary["model"])
    splits = [s for s in ["test", "ood_test", "dev"] if s in set(summary["split"])]
    labels = {"test": "In-domain test", "ood_test": "Out-of-domain test", "dev": "Dev"}

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, metric in zip(axes, ["wer", "cer"]):
        vals = {m: {labels[s]: v for s, v in summary[summary["model"] == m].set_index("split")[metric].items()
                    if s in labels} for m in models}
        bars(ax, [labels[s] for s in splits], models, vals)
        style(ax, f"{metric.upper()} (lower is better)")
    fig.tight_layout()
    fig.savefig(OUT / "fig_wer_cer.png", dpi=200)
    plt.close(fig)

    test = summary[summary["split"] == "test"]
    if not test.empty:
        fig, ax = plt.subplots(figsize=(9, 4.2))
        vals = {m: {t: test.set_index("model").at[m, f"share_{t}"] for t in TYPE_ORDER} for m in test["model"]}
        bars(ax, TYPE_ORDER, ordered(test["model"]), vals)
        style(ax, "Share of word errors by type (in-domain test)")
        fig.tight_layout()
        fig.savefig(OUT / "fig_error_types.png", dpi=200)
        plt.close(fig)

    dialect_vals = {}
    for (m, s), df in frames.items():
        if s == "test" and "dialect" in df:
            ok = df["ref_norm"] != ""
            dialect_vals[m] = {d: jiwer.wer(list(g.loc[ok, "ref_norm"]), list(g.loc[ok, "pred_norm"]))
                               for d, g in df.groupby("dialect")}
    if dialect_vals:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        bars(ax, sorted({d for v in dialect_vals.values() for d in v}), ordered(dialect_vals), dialect_vals)
        style(ax, "WER by dialect (in-domain test)")
        fig.tight_layout()
        fig.savefig(OUT / "fig_dialect.png", dpi=200)
        plt.close(fig)


def main():
    files = sorted(PRED_DIR.glob("*__*.csv"))
    if not files:
        raise SystemExit("No prediction files yet: run src/evaluate.py first.")
    OUT.mkdir(parents=True, exist_ok=True)
    rows, frames = [], {}
    for f in files:
        row, df = analyse(f)
        rows.append(row)
        frames[(row["model"], row["split"])] = df
        print(f"analysed {f.name}")
    summary = pd.DataFrame(rows).round(4)
    summary.to_csv(OUT / "summary.csv", index=False)
    figures(summary, frames)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
