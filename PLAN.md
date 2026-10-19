# TwiBench — Project Plan

**Type:** Evaluation study of ASR for Twi, with a fine-tuning experiment and a demo prototype.

**Research questions**
1. How accurately do existing multilingual ASR models (Whisper-small, MMS) transcribe Twi out of the box?
2. How much does fine-tuning Whisper-small on Twi speech improve accuracy?
3. What kinds of errors remain (orthography, ɛ/ɔ, code-switching, word segmentation, dialect)?

---

## 1. Data

| Role | Dataset | Size | Licence | Notes |
|---|---|---|---|---|
| **Main (train/dev/test)** | Ashesi Financial Inclusion Speech Dataset: Asante Twi + Akuapem Twi | ~30 h + ~38 h, ~200 speakers each | CC-BY-4.0 | Speaker ID, gender and age are in the file names; `data.csv` gives the transcript and English translation; audio is `.ogg` |
| Backup (easier download) | `ghananlpcommunity/akuapem_multispeaker_audio_transcribed` (HF) | 28.6k clips | Mirror of the Ashesi data | No speaker IDs, so harder to split fairly |
| **Out-of-domain test** | `d3vnerd/twi_dataset` (HF) | 392 test clips | MIT | Scripture-style read speech; checks generalisation beyond finance |
| Not used | Common Voice Twi (v24) | 0.3 h validated | CC0 | Too small |
| Not used | UGSpeechData (Univ. of Ghana) | ~100 h transcribed | Unclear | Access process unclear; mention in related work |

**Splitting rule (important).** In the Ashesi data, every speaker reads the *same* set of sentences, and the official 10% split overlaps with the 90% split in both speakers and sentences. So we build our own split:
- **speaker-disjoint**: no speaker appears in more than one of train/dev/test
- **sentence-disjoint**: no test sentence appears in training, so the model can't just memorise sentences
- Target split: ~80/10/10, balanced by dialect and gender.
- Check after download: how many *unique* sentences there are. If there are very few, the sentence-disjoint test set will be small, and we report that.

## 2. Models

| Model | How used | Notes |
|---|---|---|
| `openai/whisper-small` (244M) | Zero-shot | Twi isn't a Whisper language, so expect very high WER (that's a finding in itself) |
| `facebook/mms-1b-all` (1B) | Zero-shot with the `aka` (Akan) adapter | Supports Akan; licence CC-BY-NC 4.0 (fine for academic use) |
| **Whisper-small fine-tuned** | Trained on our Twi train split | The main "improving" experiment |
| MMS `aka` adapter fine-tuned (optional) | Train only the small adapter | Cheap; gives a fair "both fine-tuned" comparison |
| `GiftMark/akan-whisper-model` (optional) | Zero-shot reference | An existing community Whisper-small fine-tune for Akan |

## 3. Evaluation

- **Metrics:** WER (main) and CER, computed with `jiwer`.
- **Normalisation** (one function shared by every model): lowercase, strip punctuation, collapse spaces, write numbers consistently. Report results **with and without** folding ɛ→e and ɔ→o, which shows how much of the error is just the special letters.
- **Breakdowns:** by dialect (Asante vs Akuapem), by gender, and in-domain vs out-of-domain.
- Save every prediction to CSV so the error analysis is reproducible.

## 4. Error analysis

Categories to count and illustrate:
1. ɛ/ɔ substitutions (e.g. *yɛ* → *ye*)
2. Word-boundary errors (split/joined words)
3. English code-switching (*credit*, *network*, *cedis*)
4. Numbers and amounts
5. Dialect-specific spellings (Asante vs Akuapem)
6. Hallucination: Whisper producing fluent but wrong text (prior work flags this)

## 5. Compute

The PC has little free disk space, so **all heavy work runs on Kaggle** (free GPU, ~30 h/week).
- **Kaggle:** `notebooks/twibench.ipynb` downloads the data, builds the split, runs the baselines, fine-tunes, evaluates, and packs `twibench_results.zip` (a few MB).
- **This PC:** code only, plus the error analysis on the downloaded results. Nothing large is downloaded.
- After editing anything in `src/`, run `python notebooks/build_notebook.py` so the notebook picks up the change (a test checks this).

## 6. Deliverables

- `results/` holds the WER/CER tables (before vs after, by dialect and domain), predictions CSVs and charts
- The fine-tuned model, pushed to the Hugging Face Hub
- `app/demo.py`: a Gradio app (record or upload → transcription)
- The report: intro, related work, data, method, results, error analysis, limitations, future work

## 7. Steps (in order)

| # | Step | Done when |
|---|---|---|
| 1 | Project setup: folders, `requirements.txt`, virtual env | `pip install` succeeds |
| 2 | Download the Ashesi Asante + Akuapem data and the out-of-domain HF set | Files are in `data/raw/` |
| 3 | Data prep: parse speaker IDs, resample to 16 kHz, build the speaker- and sentence-disjoint split | `data/{train,dev,test}.csv` plus a stats table (hours, speakers, sentences) |
| 4 | Write the normalisation function and test it on examples | Unit test passes |
| 5 | Evaluation script (any model → predictions CSV → WER/CER) | Runs on 20 clips |
| 6 | Zero-shot baselines: Whisper-small and MMS-aka on the full test set | Baseline table |
| 7 | Kaggle/Colab fine-tuning notebook for Whisper-small | Model saved to the HF Hub |
| 8 | (Optional) MMS adapter fine-tune | Second fine-tuned model |
| 9 | Re-evaluate the fine-tuned models on the same test sets | Before/after table |
| 10 | Error analysis script and charts | Figures and example tables |
| 11 | Gradio demo using the best model | Runs locally |
| 12 | Write-up | Report draft |

## Related work to cite

- Mensah, Wiafe et al. (2025), *Benchmarking Akan ASR Models Across Domain-Specific Datasets*, arXiv:2507.02407. Seven Whisper/Wav2Vec2 Akan models on four domains; finds that models degrade badly out-of-domain and that Whisper's errors are fluent but misleading.
- Wiafe et al. (2025), *UGSpeechData*, Data in Brief 61, 111880.
- Ashesi / Nokwary, Financial Inclusion Speech Dataset (Lacuna Fund 2020).
- Pratap et al. (2023), *Scaling Speech Technology to 1,000+ Languages* (MMS).
- Radford et al. (2022), *Robust Speech Recognition via Large-Scale Weak Supervision* (Whisper).

**How TwiBench differs:** a direct zero-shot Whisper vs MMS comparison; a controlled before/after fine-tune on a speaker- **and** sentence-disjoint split; quantifying how much error comes from ɛ/ɔ orthography; dialect and code-switching analysis; an open, reproducible pipeline and demo.
