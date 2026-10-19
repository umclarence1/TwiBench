async function request(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new Error("Can't reach the TwiBench server. Is `python server/app.py` running?");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

export const getHealth = () => request("/api/health");
export const getExamples = (split, n = 6) => request(`/api/examples?split=${split}&n=${n}`);
export const getResults = () => request("/api/results");

export function transcribe({ blob, fileName, example, models, reference }) {
  const form = new FormData();
  if (blob) form.append("file", blob, fileName || "recording.webm");
  if (example) {
    form.append("example_split", example.split);
    form.append("example_name", example.name);
  }
  form.append("models", models.join(","));
  if (reference) form.append("reference", reference);
  return request("/api/transcribe", { method: "POST", body: form });
}

export function sendFeedback({ model, hypothesis, correction, consent, blob }) {
  const form = new FormData();
  form.append("model", model);
  form.append("hypothesis", hypothesis || "");
  form.append("correction", correction);
  form.append("consent", consent ? "true" : "false");
  if (consent && blob) form.append("file", blob, "recording.webm");
  return request("/api/feedback", { method: "POST", body: form });
}

export const pct = (x, digits = 0) => (x == null ? "–" : `${(x * 100).toFixed(digits)}%`);
