import { useEffect, useState } from "react";
import { getResults, pct } from "../api.js";
import BarChart from "./BarChart.jsx";
import Icon from "./Icon.jsx";

const SERIES = [
  { key: "whisper-small", label: "Before training", cls: "m-zeroshot" },
  { key: "whisper-small-ft", label: "After training (TwiBench)", cls: "m-finetuned" },
];
const SPLITS = [
  { key: "test", label: "Everyday Twi" },
  { key: "ood_test", label: "Bible readings" },
];

export default function ResultsPage({ go }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { getResults().then(setData).catch((e) => setError(e.message)); }, []);

  if (error) return <p className="error-text"><Icon name="alert" size={16} /> {error}</p>;
  if (!data) return <div className="panel skeleton" aria-busy="true"><div /><div /><div /></div>;

  const find = (rows, model, split) => rows.find((r) => r.model === model && r.split === split);
  const metric = (m) => (model, split) => find(data.metrics, model, split)?.[m] ?? null;
  const err = (m) => (model, split) => find(data.errors, model, split)?.[m] ?? null;
  const zs = find(data.metrics, "whisper-small", "test");
  const ft = find(data.metrics, "whisper-small-ft", "test");
  const zsE = find(data.errors, "whisper-small", "test");
  const ftE = find(data.errors, "whisper-small-ft", "test");
  const testClips = data.data.filter((d) => d.split === "test").reduce((a, d) => a + d.clips, 0) || 234;

  return (
    <div className="research">
      <div className="page-head">
        <h1>Research results</h1>
        <p>How much better does the AI understand Twi after training? We tested it on {testClips} recordings
          of everyday Twi from <b>people and sentences it had never heard</b>, plus 150 Bible readings.</p>
      </div>

      <section className="tiles" aria-label="Headline results">
        <Tile label="Word mistakes" before={zs?.wer} after={ft?.wer} note="Lower is better" />
        <Tile label="Letter mistakes" before={zs?.cer} after={ft?.cer} note="Lower is better" />
        <Tile label="Nonsense outputs" before={zsE?.hallucination_rate} after={ftE?.hallucination_rate} digits={1}
              note="Lower is better" />
        <Tile label="Perfect transcriptions" before={data.perfect?.["whisper-small/test"]}
              after={data.perfect?.["whisper-small-ft/test"]} higherIsBetter note="Higher is better" />
      </section>

      <section className="panel glossary">
        <h2><Icon name="info" /> What do these numbers mean?</h2>
        <div className="glossary-grid">
          <div><b>Word mistakes (WER)</b><p>Out of every 100 words spoken, how many the AI got wrong, missed or
            added. It can go above 100% when the AI adds lots of words that were never said.</p></div>
          <div><b>Letter mistakes (CER)</b><p>The same, counted per letter, so it shows when a word is
            <i> almost</i> right, like “ye” instead of “yɛ”.</p></div>
          <div><b>Nonsense outputs</b><p>Recordings where the AI produced runaway or repeated text
            unrelated to what was said.</p></div>
        </div>
      </section>

      <section className="panel charts">
        <BarChart title="Word mistakes (lower is better)" groups={SPLITS} series={SERIES} value={metric("wer")} />
        <BarChart title="Letter mistakes (lower is better)" groups={SPLITS} series={SERIES} value={metric("cer")} />
        <BarChart title="Nonsense outputs (lower is better)" groups={SPLITS} series={SERIES}
                  value={err("hallucination_rate")} />
        <BarChart title="Mistakes that are only an ɛ/ɔ letter" groups={SPLITS} series={SERIES}
                  value={err("share_vowel")}
                  note="After training the AI writes real Twi letters, so a few of its remaining slips are ɛ/ɔ mix-ups." />
      </section>

      <section className="panel">
        <h2>What we learned</h2>
        <div className="findings">
          <Finding n="1" title="Out of the box, the AI can't understand Twi">
            It hears Twi as English or French. “Akwaaba” came out as “A quava”.
          </Finding>
          <Finding n="2" title="Training on Twi halves the mistakes">
            Word mistakes fell from {pct(zs?.wer)} to {pct(ft?.wer)}, on voices and sentences it had never heard,
            and it now writes real Twi, including ɛ and ɔ.
          </Finding>
          <Finding n="3" title="It stopped producing nonsense">
            Runaway outputs dropped from {pct(zsE?.hallucination_rate, 1)} to {pct(ftE?.hallucination_rate, 1)} of recordings.
          </Finding>
          <Finding n="4" title="Topic matters">
            On Bible readings it improved only a little ({pct(metric("wer")("whisper-small", "ood_test"))} →{" "}
            {pct(metric("wer")("whisper-small-ft", "ood_test"))}): it learned everyday and money-related words, not Bible vocabulary.
          </Finding>
        </div>
        <p className="muted small limits">
          <b>Limits:</b> trained on a laptop for about 3 hours, on 2.5 hours of Asante Twi only. More data, more
          training and other dialects (Akuapem, Fante) would improve it further.
        </p>
        <button className="btn primary" onClick={() => go("try")}><Icon name="mic" /> Try it yourself</button>
      </section>
    </div>
  );
}

function Tile({ label, before, after, digits = 0, higherIsBetter = false, note }) {
  const better = before != null && after != null && (higherIsBetter ? after > before : after < before);
  return (
    <div className="tile">
      <span className="tile-label">{label}</span>
      <div className="tile-values">
        <div><span className="tile-tag">Before</span><span className="tile-before">{pct(before, digits)}</span></div>
        <Icon name="arrow" size={18} className="muted" />
        <div><span className="tile-tag">After</span><span className="tile-after">{pct(after, digits)}</span></div>
      </div>
      <span className={better ? "tile-note good" : "tile-note"}>
        {better && <Icon name="check" size={14} />} {better ? "Improved" : ""} · {note}
      </span>
    </div>
  );
}

function Finding({ n, title, children }) {
  return (
    <div className="finding">
      <span className="finding-n">{n}</span>
      <div><b>{title}</b><p>{children}</p></div>
    </div>
  );
}
