export const KINDS = {
  vowel: { label: "ɛ / ɔ letter", help: "Right word, but ɛ or ɔ was written as e or o (or the reverse)" },
  boundary: { label: "Joined or split", help: "Words were wrongly joined together or split apart" },
  loanword: { label: "English word", help: "A mistake on an English word used in Twi, like “credit”" },
  other: { label: "Wrong word", help: "A wrong, missing or extra word" },
};

/** Word-by-word view: what the AI wrote, with the correct word underneath each mistake. */
export default function WordDiff({ ops, compact = false }) {
  const counts = {};
  ops.forEach((o) => o.op !== "equal" && (counts[o.kind] = (counts[o.kind] || 0) + 1));

  return (
    <div className={compact ? "diff compact" : "diff"}>
      <div className="diff-words" lang="tw">
        {ops.map((o, i) => {
          if (o.op === "equal") return <span key={i} className="w ok" title="Correct">{o.hyp}</span>;
          const title = o.op === "substitute" ? `Wrote “${o.hyp}” instead of “${o.ref}”`
            : o.op === "delete" ? `Missed the word “${o.ref}”` : `Added a word that wasn't said: “${o.hyp}”`;
          return (
            <span key={i} className={`w err k-${o.kind}${o.op === "insert" ? " extra" : ""}`} title={title}>
              <span className="w-hyp">{o.op === "delete" ? "…" : o.hyp}</span>
              <span className="w-ref">{o.op === "insert" ? "not said" : o.ref}</span>
            </span>
          );
        })}
      </div>
      {!compact && (
        <ul className="diff-legend" aria-label="Key">
          <li><span className="swatch ok" /> Correct</li>
          {Object.entries(KINDS).filter(([k]) => counts[k]).map(([k, v]) => (
            <li key={k} title={v.help}><span className={`swatch k-${k}`} /> {v.label}</li>
          ))}
          {Object.keys(counts).length > 0 && <li className="muted">Small text = the correct word</li>}
        </ul>
      )}
    </div>
  );
}
