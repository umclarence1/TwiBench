import { useEffect, useRef, useState } from "react";
import { getExamples, transcribe } from "../api.js";
import Icon from "./Icon.jsx";
import ResultCard from "./ResultCard.jsx";
import Progress from "./Progress.jsx";

export default function ExamplesPage({ health }) {
  const splits = health?.splits || [{ key: "test", label: "Everyday Twi" }];
  const [split, setSplit] = useState("test");
  const [examples, setExamples] = useState([]);
  const [compare, setCompare] = useState(true);
  const [active, setActive] = useState(null);
  const [playing, setPlaying] = useState(null);
  const [busy, setBusy] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState("");
  const player = useRef(null);
  const resultRef = useRef(null);

  const load = () => {
    setError("");
    getExamples(split, 6).then(setExamples).catch((e) => setError(e.message));
  };
  useEffect(load, [split]);
  useEffect(() => () => player.current?.pause(), []);

  function play(ex) {
    if (playing === ex.name) {
      player.current?.pause();
      setPlaying(null);
      return;
    }
    player.current?.pause();
    const a = new Audio(ex.url);
    a.onended = () => setPlaying(null);
    a.play().then(() => setPlaying(ex.name)).catch(() => setError("Couldn't play this clip."));
    player.current = a;
  }

  async function run(ex) {
    setActive(ex);
    setBusy(true);
    setResponse(null);
    setError("");
    requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    try {
      setResponse(await transcribe({ example: ex, models: compare ? ["finetuned", "zeroshot"] : ["finetuned"] }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const label = (s) => (s.key === "test" ? "Everyday Twi" : "Bible readings");

  return (
    <div className="examples-page">
      <div className="page-head">
        <h1>Listen to real examples</h1>
        <p>No microphone needed. These are real Twi recordings the AI has <b>never heard before</b>.
          Play one, then see what the AI writes.</p>
      </div>

      <div className="toolbar">
        <div className="segmented" role="tablist" aria-label="Type of recording">
          {splits.map((s) => (
            <button key={s.key} role="tab" aria-selected={split === s.key}
                    className={split === s.key ? "seg active" : "seg"} onClick={() => setSplit(s.key)}>
              {label(s)}
            </button>
          ))}
        </div>
        <div className="toolbar-right">
          <label className="switch small-switch">
            <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} />
            <span className="switch-track" aria-hidden="true" />
            <span>Show the AI before training too</span>
          </label>
          <button className="btn secondary" onClick={load}><Icon name="refresh" size={16} /> New examples</button>
        </div>
      </div>
      {split === "ood_test" && (
        <p className="notice info"><Icon name="info" size={18} /> Bible readings use words the AI didn't learn
          (it was trained on everyday and money-related Twi), so expect more mistakes here.</p>
      )}
      {error && <p className="error-text"><Icon name="alert" size={16} /> {error}</p>}

      <div className="example-grid">
        {examples.map((ex) => (
          <article key={ex.name} className={active?.name === ex.name ? "example-card active" : "example-card"}>
            <button className={playing === ex.name ? "play-btn on" : "play-btn"} onClick={() => play(ex)}
                    aria-label={playing === ex.name ? "Pause" : `Play “${ex.text}”`}>
              <Icon name={playing === ex.name ? "stop" : "play"} size={20} />
            </button>
            <div className="example-body">
              <span className="example-label">The speaker says</span>
              <p className="example-text" lang="tw">{ex.text}</p>
              <span className="muted small">{ex.duration} seconds{ex.speaker ? ` · ${ex.speaker} voice` : ""}</span>
            </div>
            <button className="btn primary sm" onClick={() => run(ex)} disabled={busy}>
              {busy && active?.name === ex.name ? "Working…" : "See what the AI writes"}
            </button>
          </article>
        ))}
      </div>

      <div ref={resultRef}>
        {(busy || response) && (
          <section className="example-result">
            <h2>Result for <span lang="tw">“{active?.text}”</span></h2>
            {busy && <Progress firstLoad={false} slow={compare} />}
            {response && (
              <div className={response.results.length > 1 ? "compare-grid" : ""}>
                {response.results.map((r) => <ResultCard key={r.model} result={r} />)}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
