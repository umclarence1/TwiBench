"""Step 11: TwiBench demo — record or upload Twi speech and see the transcription.

Uses the fine-tuned model in models/whisper-small-twi if it exists, otherwise
zero-shot Whisper-small. Both can be shown side by side for comparison.

Usage:
    python app/demo.py              # opens http://127.0.0.1:7860
"""
import sys
from pathlib import Path

import gradio as gr
import librosa

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from evaluate import SR, WhisperASR  # noqa: E402

FINETUNED = ROOT / "models" / "whisper-small-twi"
PROXY_LANG = "yoruba"  # must match the language token used in fine-tuning

_models = {}


def get_model(name):
    if name not in _models:
        if name == "fine-tuned":
            _models[name] = WhisperASR(str(FINETUNED), language=PROXY_LANG)
        else:
            _models[name] = WhisperASR("openai/whisper-small")
    return _models[name]


def transcribe(audio_path, compare):
    if not audio_path:
        return "Please record or upload some Twi speech first.", ""
    y, _ = librosa.load(audio_path, sr=SR, mono=True)
    if len(y) > 30 * SR:
        y = y[:30 * SR]  # Whisper handles up to 30 s per pass
    main = "fine-tuned" if FINETUNED.exists() else "zero-shot"
    text = get_model(main)([y])[0].strip()
    other = get_model("zero-shot")([y])[0].strip() if compare and main == "fine-tuned" else ""
    return text, other


def build():
    status = ("Using the **fine-tuned** Twi model." if FINETUNED.exists()
              else "Fine-tuned model not found yet — using **zero-shot Whisper-small** (expect poor Twi output).")
    with gr.Blocks(title="TwiBench demo") as demo:
        gr.Markdown(f"# TwiBench: Twi speech recognition\n{status}\n\n"
                    "Record or upload up to 30 seconds of Twi speech, then press **Transcribe**.")
        audio = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Twi speech")
        compare = gr.Checkbox(label="Also show the zero-shot Whisper-small output", value=False,
                              visible=FINETUNED.exists())
        btn = gr.Button("Transcribe", variant="primary")
        out = gr.Textbox(label="Transcription", lines=3)
        out_zero = gr.Textbox(label="Zero-shot Whisper-small (for comparison)", lines=3,
                              visible=FINETUNED.exists())
        btn.click(transcribe, [audio, compare], [out, out_zero])
    return demo


if __name__ == "__main__":
    build().launch()
