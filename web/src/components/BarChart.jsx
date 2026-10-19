import { useState } from "react";

/** Grouped bar chart (percentages) with hover tooltips, legend and a table view.
 *  groups: [{key,label}], series: [{key,label,cls}], value(seriesKey, groupKey) -> number|null */
export default function BarChart({ title, groups, series, value, note }) {
  const [hover, setHover] = useState(null);
  const [table, setTable] = useState(false);

  const W = 560, H = 260, M = { t: 22, r: 8, b: 34, l: 44 };
  const values = groups.flatMap((g) => series.map((s) => value(s.key, g.key))).filter((v) => v != null);
  // Scale to the data (so small rates stay readable), with 3-5 round gridlines.
  const top = Math.max(0.05, ...values) * 1.15;
  const step = [0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1].find((s) => top / s <= 5) || 1;
  const max = Math.ceil(top / step) * step;
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step);
  const y = (v) => M.t + (H - M.t - M.b) * (1 - v / max);
  const gw = (W - M.l - M.r) / groups.length;
  const bw = Math.min(56, (gw * 0.7) / series.length);
  const fmt = (v) => `${Math.round(v * 100)}%`;

  return (
    <figure className="chart">
      <figcaption className="row-between">
        <span className="chart-title">{title}</span>
        <button className="link small" onClick={() => setTable(!table)}>{table ? "Show chart" : "Show table"}</button>
      </figcaption>
      <ul className="legend">
        {series.map((s) => <li key={s.key}><span className={`swatch ${s.cls}`} />{s.label}</li>)}
      </ul>
      {table ? (
        <table className="data-table">
          <thead><tr><th />{series.map((s) => <th key={s.key}>{s.label}</th>)}</tr></thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.key}><th>{g.label}</th>
                {series.map((s) => <td key={s.key}>{value(s.key, g.key) == null ? "–" : fmt(value(s.key, g.key))}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="chart-wrap">
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title}>
            {ticks.map((t) => (
              <g key={t}>
                <line x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} className="grid" />
                <text x={M.l - 8} y={y(t)} dy="0.32em" textAnchor="end" className="tick">{fmt(t)}</text>
              </g>
            ))}
            {groups.map((g, gi) => {
              const cx = M.l + gw * gi + gw / 2;
              return (
                <g key={g.key}>
                  {series.map((s, si) => {
                    const v = value(s.key, g.key);
                    if (v == null) return null;
                    const x = cx + (si - (series.length - 1) / 2) * (bw + 2) - bw / 2;
                    const h = Math.max(1, y(0) - y(v));
                    return (
                      <g key={s.key} onMouseEnter={() => setHover({ g, s, v, x: x + bw / 2, y: y(v) })}
                         onMouseLeave={() => setHover(null)}>
                        <rect x={x - 4} y={M.t} width={bw + 8} height={H - M.t - M.b} fill="transparent" />
                        <path className={`bar ${s.cls}`}
                              d={`M${x},${y(0)} V${y(0) - h + 4} q0,-4 4,-4 h${bw - 8} q4,0 4,4 V${y(0)} Z`} />
                        <text x={x + bw / 2} y={y(v) - 6} textAnchor="middle" className="bar-label">{fmt(v)}</text>
                      </g>
                    );
                  })}
                  <text x={cx} y={H - M.b + 20} textAnchor="middle" className="group-label">{g.label}</text>
                </g>
              );
            })}
            <line x1={M.l} x2={W - M.r} y1={y(0)} y2={y(0)} className="axis" />
          </svg>
          {hover && (
            <div className="tooltip" style={{ left: `${(hover.x / W) * 100}%`, top: `${(hover.y / H) * 100}%` }}>
              <b>{hover.s.label}</b><br />{hover.g.label}: {fmt(hover.v)}
            </div>
          )}
        </div>
      )}
      {note && <p className="muted small">{note}</p>}
    </figure>
  );
}
