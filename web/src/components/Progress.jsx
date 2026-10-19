import { useEffect, useState } from "react";
import Icon from "./Icon.jsx";

const STEPS = ["Sending your audio", "Listening to the Twi", "Writing it down"];

/** Friendly progress indicator while a transcription runs. */
export default function Progress({ firstLoad, slow }) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const t1 = setTimeout(() => setStep(1), 700);
    const t2 = setTimeout(() => setStep(2), firstLoad ? 15000 : 2500);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [firstLoad]);

  return (
    <div className="progress-card" aria-busy="true" aria-live="polite">
      <ol className="progress-steps">
        {STEPS.map((s, i) => (
          <li key={s} className={i < step ? "done" : i === step ? "current" : ""}>
            <span className="progress-icon">
              {i < step ? <Icon name="check" size={16} /> : i === step ? <Icon name="spinner" size={16} className="spin" /> : null}
            </span>
            {s}
          </li>
        ))}
      </ol>
      {firstLoad && <p className="muted small">First use: the AI is starting up. This takes about 30 seconds, then it's quicker.</p>}
      {slow && <p className="muted small">The original AI is slower, so the comparison adds a few seconds.</p>}
    </div>
  );
}
