import { useState } from "react";
import Icon from "./Icon.jsx";

const FAQ = [
  {
    q: "What is TwiBench?",
    a: <>TwiBench turns spoken <b>Twi</b> into written text. You speak, and it types what you said, like voice
      typing on a phone. It is a research project studying how well AI can learn Ghanaian languages.</>,
  },
  {
    q: "How do I use it?",
    a: <ol><li>Open <b>Try it</b>.</li><li>Tap the microphone and allow access if your browser asks.</li>
      <li>Say a short sentence in Twi, then tap again to stop.</li><li>The text appears in a few seconds.</li></ol>,
  },
  {
    q: "Why does it get some words wrong?",
    a: <>It learned from only about 2.5 hours of recordings, mostly everyday and money-related phrases in
      Asante Twi. Unfamiliar topics, other dialects, background noise and long sentences make it harder.
      Most phone voice assistants learn from many thousands of hours.</>,
  },
  {
    q: "How do I type ɛ and ɔ?",
    a: <>Use the <b>ɛ ɔ Ɛ Ɔ</b> buttons next to any text box. They insert the letter where your cursor is.</>,
  },
  {
    q: "Is my voice saved?",
    a: <>No. Your recording is used only to produce the text. It is saved <b>only</b> if you correct a result
      and tick “Also share my recording”, so it can help train better Twi AI.</>,
  },
  {
    q: "The microphone doesn't work. What can I do?",
    a: <>Click the lock icon next to the web address, set <b>Microphone</b> to <b>Allow</b>, and reload the page.
      Make sure no other app is using the microphone. You can also <b>upload</b> a recording instead
      (MP3, WAV, M4A, OGG or WEBM, up to 30 seconds).</>,
  },
  {
    q: "How was it built?",
    a: <>We started from <b>Whisper-small</b>, an open speech-recognition AI by OpenAI that was never taught Twi.
      We trained it further on Asante Twi recordings from 183 speakers (the Ashesi Financial Inclusion Speech
      Dataset), then tested it on different speakers and sentences to measure the improvement fairly.</>,
  },
  {
    q: "What does “word error rate” mean?",
    a: <>Out of every 100 words spoken, how many the AI got wrong, missed or added. Lower is better. It went
      from 173% before training to 80% after. See <b>Research</b> for details.</>,
  },
];

export default function AboutPage({ go }) {
  const [open, setOpen] = useState(0);
  return (
    <div className="about">
      <div className="page-head">
        <h1>Help &amp; About</h1>
        <p>Answers to common questions. New here? Start with the first one.</p>
      </div>

      <div className="faq">
        {FAQ.map((item, i) => (
          <div key={item.q} className={open === i ? "faq-item open" : "faq-item"}>
            <button className="faq-q" onClick={() => setOpen(open === i ? -1 : i)} aria-expanded={open === i}
                    aria-controls={`faq-${i}`}>
              {item.q} <Icon name="chevron" size={18} className={open === i ? "rot" : ""} />
            </button>
            {open === i && <div className="faq-a" id={`faq-${i}`}>{item.a}</div>}
          </div>
        ))}
      </div>

      <section className="panel credits">
        <h2>Credits</h2>
        <ul>
          <li><b>Speech data:</b> Ashesi University &amp; Nokwary Technologies, Financial Inclusion Speech
            Dataset (CC-BY-4.0), via the GhanaNLP Hugging Face mirror.</li>
          <li><b>Bible reading test clips:</b> d3vnerd/twi_dataset (MIT).</li>
          <li><b>Base AI model:</b> OpenAI Whisper-small (MIT).</li>
        </ul>
        <button className="btn primary" onClick={() => go("try")}><Icon name="mic" /> Try it now</button>
      </section>
    </div>
  );
}
