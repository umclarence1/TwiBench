import { useState } from "react";
import { pct } from "../api.js";
import Icon from "./Icon.jsx";
import WordDiff from "./WordDiff.jsx";
import { useToast } from "./Toast.jsx";

export const MODEL_NAMES = {
  finetuned: { name: "TwiBench", sub: "trained on Twi" },
  zeroshot: { name: "Original AI", sub: "before training on Twi" },
};

export function verdict(score) {
  const right = score.ops.filter((o) => o.op === "equal").length;
  const share = score.words ? right / score.words : 0;
  if (score.wer === 0) return { right, share, tone: "great", text: "Perfect match" };
  if (share >= 0.7) return { right, share, tone: "good", text: "Very close" };
  if (share >= 0.4) return { right, share, tone: "ok", text: "Partly right" };
  return { right, share, tone: "low", text: "The AI struggled with this one" };
}

export default function ResultCard({ result, variant = "main" }) {
  const toast = useToast();
  const [details, setDetails] = useState(false);
  const { model, text, seconds, score } = result;
  const name = MODEL_NAMES[model] || { name: result.label, sub: "" };
  const v = score ? verdict(score) : null;

  function copy() {
    navigator.clipboard?.writeText(text).then(() => toast("Text copied")).catch(() => toast("Couldn't copy", "warn"));
  }

  return (
    <article className={`result-card ${variant} m-${model}`}>
      <header className="result-head">
        <span className={`model-badge m-${model}`}>
          <span className="badge-dot" /> {name.name} <span className="muted">· {name.sub}</span>
        </span>
        {text && (
          <button className="icon-btn" onClick={copy} aria-label="Copy text" title="Copy text">
            <Icon name="copy" size={18} />
          </button>
        )}
      </header>

      <p className={variant === "main" ? "transcript" : "transcript sm"} lang="tw">
        {text || <span className="muted">No words were recognised. Try recording again a little louder.</span>}
      </p>

      {v && (
        <div className={`accuracy ${v.tone}`}>
          <div className="accuracy-top">
            <span className="accuracy-count"><b>{v.right}</b> of {score.words} words correct</span>
            <span className="accuracy-verdict">{v.text}</span>
          </div>
          <div className="accuracy-bar" role="meter" aria-valuemin={0} aria-valuemax={score.words}
               aria-valuenow={v.right} aria-label="Words correct">
            <span style={{ width: `${v.share * 100}%` }} />
          </div>
        </div>
      )}
      {score && <WordDiff ops={score.ops} compact={variant !== "main"} />}

      <button className="details-toggle" onClick={() => setDetails(!details)} aria-expanded={details}>
        Details <Icon name="chevron" size={16} className={details ? "rot" : ""} />
      </button>
      {details && (
        <dl className="details">
          {score && <><dt>Word error rate</dt><dd>{pct(score.wer)}</dd>
            <dt>Letter error rate</dt><dd>{pct(score.cer)}</dd></>}
          <dt>Processing time</dt><dd>{seconds} s</dd>
          <dt>Model</dt><dd>{result.label}</dd>
        </dl>
      )}
    </article>
  );
}
