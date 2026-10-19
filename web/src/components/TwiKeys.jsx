import { useRef } from "react";

const LETTERS = ["ɛ", "ɔ", "Ɛ", "Ɔ"];

/** Text box with buttons for the Twi letters most keyboards don't have. */
export default function TwiInput({ value, onChange, placeholder, id, label, hint }) {
  const ref = useRef(null);

  function insert(ch) {
    const el = ref.current;
    const start = el.selectionStart ?? value.length;
    const end = el.selectionEnd ?? value.length;
    onChange(value.slice(0, start) + ch + value.slice(end));
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(start + 1, start + 1);
    });
  }

  return (
    <div className="twi-input">
      {label && <label htmlFor={id}>{label}</label>}
      {hint && <p className="field-hint">{hint}</p>}
      <div className="twi-input-row">
        <input id={id} ref={ref} type="text" value={value} placeholder={placeholder} lang="tw"
               onChange={(e) => onChange(e.target.value)} autoComplete="off" spellCheck={false} />
        <div className="twi-keys" role="group" aria-label="Twi letters">
          {LETTERS.map((ch) => (
            <button key={ch} type="button" className="key" onClick={() => insert(ch)} aria-label={`Type ${ch}`}>
              {ch}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
