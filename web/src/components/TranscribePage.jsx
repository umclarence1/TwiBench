import { useEffect, useRef, useState } from "react";
import { transcribe } from "../api.js";
import Icon from "./Icon.jsx";
import Recorder from "./Recorder.jsx";
import ResultCard from "./ResultCard.jsx";
import Feedback from "./Feedback.jsx";
import Progress from "./Progress.jsx";
import TwiInput from "./TwiKeys.jsx";

const PHRASES = [
  { tw: "Akwaaba", en: "Welcome" },
  { tw: "Medaase", en: "Thank you" },
  { tw: "Wo ho te sɛn?", en: "How are you?" },
  { tw: "Ɛkɔm de me", en: "I am hungry" },
  { tw: "Mepɛ sɛ metɔ credit", en: "I want to buy airtime" },
  { tw: "Me sika no aka ahe?", en: "How much of my money is left?" },
];
const HISTORY_KEY = "twibench-history";

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; } catch { return []; }
}

export default function TranscribePage({ health }) {
  const [phrase, setPhrase] = useState(null);
  const [reference, setReference] = useState("");
  const [compare, setCompare] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [audio, setAudio] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [response, setResponse] = useState(null);
  const [history, setHistory] = useState(loadHistory);
  const resultRef = useRef(null);

  useEffect(() => {
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 6))); } catch { /* not available */ }
  }, [history]);

  const finetunedReady = health?.models.find((m) => m.key === "finetuned")?.available !== false;
  const models = [finetunedReady ? "finetuned" : "zeroshot", ...(compare && finetunedReady ? ["zeroshot"] : [])];
  const [warm, setWarm] = useState(() => new Set());  // models already loaded on the server
  const firstLoad = !!health && models.some((k) => !warm.has(k) && !health.models.find((m) => m.key === k)?.loaded);

  function choosePhrase(p) {
    const same = phrase?.tw === p.tw;
    setPhrase(same ? null : p);
    setReference(same ? "" : p.tw);
  }

  async function run(a) {
    setAudio(a);
    setBusy(true);
    setError("");
    setResponse(null);
    requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }));
    try {
      const r = await transcribe({ blob: a.blob, fileName: a.fileName, models, reference: reference.trim() });
      setResponse(r);
      const main = r.results[0];
      setHistory((h) => [{ time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                           text: main.text }, ...h].slice(0, 6));
      setWarm((w) => new Set([...w, ...models]));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="try">
      <div className="page-head">
        <h1>Try TwiBench</h1>
        <p>Say a short sentence in Twi. The text appears automatically when you stop.</p>
      </div>

      <div className="try-grid">
        <section className="panel speak-panel" aria-labelledby="speak-title">
          <h2 id="speak-title" className="sr-only">Speak</h2>
          {phrase && (
            <div className="read-aloud">
              <span className="read-label">Read this aloud</span>
              <span className="read-text" lang="tw">{phrase.tw}</span>
              <span className="read-meaning">“{phrase.en}”</span>
            </div>
          )}

          <Recorder maxSeconds={health?.max_seconds || 30} onAudio={run} disabled={busy} />

          <div className="phrases">
            <p className="phrases-title">Not sure what to say? Pick a phrase:</p>
            <div className="chips">
              {PHRASES.map((p) => (
                <button key={p.tw} className={phrase?.tw === p.tw ? "chip active" : "chip"}
                        onClick={() => choosePhrase(p)} aria-pressed={phrase?.tw === p.tw}>
                  <span lang="tw">{p.tw}</span>
                  <span className="chip-en">{p.en}</span>
                </button>
              ))}
            </div>
          </div>

          <button className="details-toggle" onClick={() => setShowOptions(!showOptions)} aria-expanded={showOptions}>
            More options <Icon name="chevron" size={16} className={showOptions ? "rot" : ""} />
          </button>
          {showOptions && (
            <div className="options">
              <label className="switch">
                <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)}
                       disabled={!finetunedReady} />
                <span className="switch-track" aria-hidden="true" />
                <span>
                  <b>Compare with the original AI</b>
                  <span className="field-hint">See what the AI wrote before it was trained on Twi (slower).</span>
                </span>
              </label>
              <TwiInput id="reference" label="What will you say? (optional)" value={reference}
                        onChange={(v) => { setReference(v); setPhrase(null); }}
                        hint="If you type it, we'll show how many words the AI got right."
                        placeholder="e.g. Me sika no aka ahe?" />
            </div>
          )}
        </section>

        <section className="results-col" ref={resultRef} aria-live="polite" aria-label="Result">
          {busy && <Progress firstLoad={firstLoad} slow={models.includes("zeroshot") && models.length > 1} />}
          {error && (
            <div className="panel error-panel" role="alert">
              <Icon name="alert" /> <div><b>Something went wrong.</b><p>{error}</p></div>
            </div>
          )}
          {!busy && !response && !error && <EmptyState />}
          {response && (
            <>
              <ResultCard result={response.results[0]} />
              {audio && (
                <div className="playback">
                  <Icon name="volume" size={18} /> <span>Your recording</span>
                  <audio controls src={audio.url} />
                </div>
              )}
              {response.results.slice(1).map((r) => <ResultCard key={r.model} result={r} variant="compare" />)}
              <Feedback key={response.results[0].text + audio?.url} result={response.results[0]}
                        initial={reference.trim()} blob={audio?.blob} />
            </>
          )}
          {history.length > 0 && (
            <div className="history">
              <div className="row-between">
                <h3>Recent</h3>
                <button className="text-btn" onClick={() => setHistory([])}>Clear</button>
              </div>
              <ul>
                {history.map((h, i) => (
                  <li key={i}><span className="muted">{h.time}</span><span lang="tw">{h.text || "—"}</span></li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="panel empty-state">
      <div className="empty-icon"><Icon name="wave" size={28} /></div>
      <h3>Your text will appear here</h3>
      <ol className="mini-steps">
        <li><span>1</span> Tap the microphone</li>
        <li><span>2</span> Say a short Twi sentence</li>
        <li><span>3</span> Tap again to stop. Done!</li>
      </ol>
      <p className="muted small">Tip: pick one of the suggested phrases first, and we’ll show how many words the AI got right.</p>
    </div>
  );
}
