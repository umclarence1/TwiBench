import { useEffect, useState } from "react";
import { getHealth } from "./api.js";
import Icon from "./components/Icon.jsx";
import { ToastProvider } from "./components/Toast.jsx";
import HomePage from "./components/HomePage.jsx";
import TranscribePage from "./components/TranscribePage.jsx";
import ExamplesPage from "./components/ExamplesPage.jsx";
import ResultsPage from "./components/ResultsPage.jsx";
import AboutPage from "./components/AboutPage.jsx";

const PAGES = [
  { key: "home", label: "Home", icon: "home" },
  { key: "try", label: "Try it", icon: "mic" },
  { key: "examples", label: "Examples", icon: "wave" },
  { key: "research", label: "Research", icon: "chart" },
  { key: "about", label: "Help & About", icon: "info" },
];

const pageFromHash = () => {
  const h = window.location.hash.replace("#", "");
  return PAGES.some((p) => p.key === h) ? h : "home";
};

export default function App() {
  const [page, setPage] = useState(pageFromHash);
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState("");

  useEffect(() => {
    getHealth().then(setHealth).catch((e) => setHealthError(e.message));
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const go = (key) => {
    window.location.hash = key;
    setPage(key);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const finetuned = health?.models.find((m) => m.key === "finetuned");

  return (
    <ToastProvider>
      <a className="skip" href="#main">Skip to content</a>
      <header className="topbar">
        <div className="topbar-inner">
          <button className="brand" onClick={() => go("home")} aria-label="TwiBench home">
            <span className="logo" aria-hidden="true"><Icon name="wave" size={18} /></span>
            <span className="brand-name">TwiBench</span>
          </button>
          <nav className="nav" aria-label="Main">
            {PAGES.map((p) => (
              <a key={p.key} href={`#${p.key}`} className={page === p.key ? "nav-link active" : "nav-link"}
                 aria-current={page === p.key ? "page" : undefined}
                 onClick={(e) => { e.preventDefault(); go(p.key); }}>
                <Icon name={p.icon} size={17} /> <span>{p.label}</span>
              </a>
            ))}
          </nav>
        </div>
      </header>

      {healthError && (
        <div className="notice error container"><Icon name="alert" /> {healthError}</div>
      )}
      {health && !finetuned?.available && (
        <div className="notice warn container">
          <Icon name="alert" /> The trained Twi model wasn't found, so only the original (untrained) AI is available.
        </div>
      )}

      <main id="main" className="container">
        {page === "home" && <HomePage go={go} />}
        {page === "try" && <TranscribePage health={health} />}
        {page === "examples" && <ExamplesPage health={health} />}
        {page === "research" && <ResultsPage go={go} />}
        {page === "about" && <AboutPage go={go} />}
      </main>

      <footer className="site-footer">
        <div className="container footer-inner">
          <div>
            <div className="brand-name small-brand">TwiBench</div>
            <p>Speech recognition research for Twi, one of Ghana’s major languages.</p>
          </div>
          <div className="footer-credits">
            <p>Model: OpenAI Whisper-small, fine-tuned on Asante Twi.</p>
            <p>Data: Ashesi University &amp; Nokwary Technologies, Financial Inclusion Speech Dataset (CC-BY-4.0).</p>
          </div>
        </div>
      </footer>
    </ToastProvider>
  );
}
