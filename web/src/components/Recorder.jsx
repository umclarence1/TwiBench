import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";

/** One big microphone button. Calls onAudio({blob, fileName, url, source}) when a
 *  recording finishes or a file is chosen. */
export default function Recorder({ maxSeconds = 30, onAudio, disabled }) {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [level, setLevel] = useState(0);
  const [error, setError] = useState("");
  const rec = useRef(null);
  const fileInput = useRef(null);

  useEffect(() => () => cleanup(), []);

  function cleanup() {
    const r = rec.current;
    if (!r) return;
    cancelAnimationFrame(r.raf);
    clearInterval(r.timer);
    r.stream.getTracks().forEach((t) => t.stop());
    r.ctx.close().catch(() => {});
    rec.current = null;
  }

  async function start() {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("This browser can't record audio. Try Chrome or Edge, or upload a file instead.");
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("permission");
      return;
    }
    const media = new MediaRecorder(stream);
    const chunks = [];
    const t0 = Date.now();
    media.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    media.onstop = () => {
      const seconds = (Date.now() - t0) / 1000;
      cleanup();
      setRecording(false);
      setLevel(0);
      if (seconds < 0.6) {
        setError("That was very short. Hold on a moment longer and speak a full phrase.");
        return;
      }
      const blob = new Blob(chunks, { type: media.mimeType || "audio/webm" });
      onAudio({ blob, fileName: "recording.webm", url: URL.createObjectURL(blob), source: "mic" });
    };

    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    ctx.createMediaStreamSource(stream).connect(analyser);
    const buf = new Uint8Array(analyser.fftSize);
    rec.current = { media, stream, ctx, raf: 0, timer: 0 };
    const tick = () => {
      analyser.getByteTimeDomainData(buf);
      let peak = 0;
      for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
      setLevel(Math.min(1, (peak / 128) * 1.8));
      if (rec.current) rec.current.raf = requestAnimationFrame(tick);
    };
    rec.current.timer = setInterval(() => {
      const s = (Date.now() - t0) / 1000;
      setElapsed(s);
      if (s >= maxSeconds) stop();
    }, 100);
    tick();
    setElapsed(0);
    setRecording(true);
    media.start();
  }

  function stop() {
    const r = rec.current;
    if (r && r.media.state !== "inactive") r.media.stop();
  }

  function onFile(e) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    if (f.size > 25 * 1024 * 1024) {
      setError("That file is too large. Please use a recording under 25 MB.");
      return;
    }
    setError("");
    onAudio({ blob: f, fileName: f.name, url: URL.createObjectURL(f), source: "file" });
  }

  const remaining = Math.max(0, maxSeconds - elapsed);

  return (
    <div className="recorder">
      <button className={`mic-button${recording ? " live" : ""}`} onClick={recording ? stop : start}
              disabled={disabled && !recording} style={{ "--level": level }}
              aria-label={recording ? "Stop recording" : "Start recording"}>
        <span className="mic-ring" aria-hidden="true" />
        <Icon name={recording ? "stop" : "mic"} size={40} />
      </button>
      <p className="mic-status" aria-live="polite">
        {recording ? (
          <><span className="rec-dot" /> Listening… tap to stop <span className="muted">({Math.ceil(remaining)} s left)</span></>
        ) : disabled ? "Working on your last recording…" : "Tap the microphone and speak in Twi"}
      </p>

      {!recording && (
        <button className="btn link-btn" onClick={() => fileInput.current.click()} disabled={disabled}>
          <Icon name="upload" size={16} /> Or upload an audio file
        </button>
      )}
      <input ref={fileInput} type="file" accept="audio/*,video/webm,.m4a,.mp3,.wav,.ogg,.flac" hidden onChange={onFile} />

      {error === "permission" ? (
        <div className="help-box" role="alert">
          <b>Microphone access is blocked.</b>
          <ol>
            <li>Click the <b>lock icon</b> next to the web address at the top of your browser.</li>
            <li>Set <b>Microphone</b> to <b>Allow</b>, then reload the page.</li>
          </ol>
          <span className="muted small">Or upload an audio file instead.</span>
        </div>
      ) : error ? (
        <p className="error-text" role="alert"><Icon name="alert" size={16} /> {error}</p>
      ) : null}
    </div>
  );
}
