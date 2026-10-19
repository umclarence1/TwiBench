import { useEffect, useState } from "react";
import { getResults } from "../api.js";
import Icon from "./Icon.jsx";

// A speech-like waveform for the illustration
const BAR_HEIGHTS = [20, 35, 60, 85, 55, 30, 45, 75, 100, 70, 40, 25, 50, 80, 95, 60, 35, 55, 70, 45, 30, 50, 35, 20];

export default function HomePage({ go }) {
  const [stats, setStats] = useState(null);
  useEffect(() => {
    getResults().then((r) => {
      const m = (model) => r.metrics.find((x) => x.model === model && x.split === "test");
      const before = m("whisper-small")?.wer, after = m("whisper-small-ft")?.wer;
      setStats({
        reduction: before && after ? Math.round((1 - after / before) * 100) : null,
        perfect: r.perfect?.["whisper-small-ft/test"],
        speakers: r.data.filter((d) => d.split === "train").reduce((a, d) => a + d.speakers, 0),
      });
    }).catch(() => {});
  }, []);

  return (
    <div className="home">
      <section className="hero">
        <div className="hero-text">
          <span className="eyebrow"><Icon name="sparkle" size={14} /> Speech recognition for Twi</span>
          <h1>Speak Twi.<br />See it written.</h1>
          <p className="lead">
            TwiBench listens to spoken Twi and types out what was said, like voice typing on your phone,
            but for one of Ghana’s most widely spoken languages.
          </p>
          <div className="hero-actions">
            <button className="btn primary lg" onClick={() => go("try")}>
              <Icon name="mic" /> Try it now
            </button>
            <button className="btn secondary lg" onClick={() => go("examples")}>
              <Icon name="play" /> Listen to examples
            </button>
          </div>
          <p className="fine">Free · No sign-up · Works in your browser</p>
        </div>

        <div className="hero-demo" aria-hidden="true">
          <div className="demo-card">
            <div className="demo-row">
              <span className="demo-mic"><Icon name="mic" size={22} /></span>
              <div className="bars">
                {BAR_HEIGHTS.map((h, i) => <span key={i} style={{ "--i": i, height: `${h}%` }} />)}
              </div>
            </div>
            <div className="demo-arrow"><Icon name="arrow" /></div>
            <div className="demo-out">
              <span className="demo-label">TwiBench wrote</span>
              <span className="demo-text">Ɛkɔm de me</span>
              <span className="demo-meaning">“I am hungry”</span>
            </div>
          </div>
        </div>
      </section>

      <section className="stat-strip" aria-label="Key results">
        <Stat value={stats?.reduction != null ? `${stats.reduction}%` : "≈50%"} label="fewer word errors after training on Twi" />
        <Stat value={stats?.perfect != null ? `${Math.round(stats.perfect * 100)}%` : "15%"} label="of new test recordings transcribed perfectly" />
        <Stat value={stats?.speakers || 183} label="Twi speakers in the training recordings" />
        <Stat value="2.5 h" label="of recorded Twi speech the AI learned from" />
      </section>

      <section className="section">
        <h2 className="section-title">How it works</h2>
        <p className="section-sub">Three simple steps. No technical knowledge needed.</p>
        <div className="steps-grid">
          <Step n="1" icon="mic" title="Speak" text="Press the microphone and say a short sentence in Twi, or upload a recording." />
          <Step n="2" icon="wave" title="The AI listens" text="An AI model trained on Twi recordings turns the sound into written Twi, including ɛ and ɔ." />
          <Step n="3" icon="edit" title="Read & improve" text="See the text in seconds. If something is wrong, correct it to help make Twi AI better." />
        </div>
      </section>

      <section className="section two-col">
        <div className="panel">
          <h3><Icon name="target" /> Works best when you…</h3>
          <ul className="ticks">
            <li>speak <b>Asante Twi</b> in short sentences (up to 30 seconds)</li>
            <li>record in a <b>quiet place</b>, close to the microphone</li>
            <li>use everyday phrases: greetings, numbers, mobile money, airtime</li>
          </ul>
        </div>
        <div className="panel">
          <h3><Icon name="shield" /> Your privacy</h3>
          <ul className="ticks">
            <li>Your recording is used only to produce the text</li>
            <li>It is <b>not saved</b> unless you choose to donate it</li>
            <li>No account, no tracking</li>
          </ul>
        </div>
      </section>

      <section className="cta-band">
        <div>
          <h2>Ready to try?</h2>
          <p>It takes about 10 seconds. Say “Akwaaba” and see what happens.</p>
        </div>
        <button className="btn primary lg" onClick={() => go("try")}><Icon name="mic" /> Start speaking</button>
      </section>
    </div>
  );
}

function Stat({ value, label }) {
  return (
    <div className="stat">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

function Step({ n, icon, title, text }) {
  return (
    <div className="step">
      <div className="step-icon"><Icon name={icon} size={22} /><span className="step-n">{n}</span></div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
