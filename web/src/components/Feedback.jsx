import { useState } from "react";
import { sendFeedback } from "../api.js";
import Icon from "./Icon.jsx";
import TwiInput from "./TwiKeys.jsx";
import { useToast } from "./Toast.jsx";

/** "Not quite right?" — users correct the text and, only if they opt in, donate their recording. */
export default function Feedback({ result, initial, blob }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(initial || result.text || "");
  const [consent, setConsent] = useState(false);
  const [state, setState] = useState("idle");

  async function submit(e) {
    e.preventDefault();
    setState("sending");
    try {
      await sendFeedback({ model: result.model, hypothesis: result.text, correction: text, consent, blob });
      setState("done");
      toast("Thank you! Your correction was saved.");
    } catch (err) {
      setState("idle");
      toast(err.message, "warn");
    }
  }

  if (state === "done")
    return <p className="thanks"><Icon name="check" /> Thanks for helping improve Twi speech technology.</p>;

  if (!open)
    return (
      <button className="feedback-open" onClick={() => setOpen(true)}>
        <Icon name="message" size={18} /> Not quite right? <b>Correct it</b> to help us improve
      </button>
    );

  return (
    <form className="feedback" onSubmit={submit}>
      <h3>What did you actually say?</h3>
      <TwiInput id="fb-text" value={text} onChange={setText} placeholder="Type the correct Twi" />
      {blob && (
        <label className="check">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          <span>Also share my recording so it can help train better Twi AI.
            <span className="muted"> Optional. Without this tick, your voice is not saved.</span></span>
        </label>
      )}
      <div className="row">
        <button className="btn primary" disabled={!text.trim() || state === "sending"}>
          {state === "sending" ? "Sending…" : "Send correction"}
        </button>
        <button type="button" className="btn ghost" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  );
}
