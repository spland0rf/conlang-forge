// Hand-built SVG charts: stacked columns over time, ranked bars. Colour = identity (fixed order), legend always shown,
// hover tooltips, and a table view for anyone who prefers numbers.
import { h } from "./ui.js";
const NS = "http://www.w3.org/2000/svg";
const svg = (tag, attrs = {}, ...kids) => {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  kids.forEach((k) => e.append(k)); return e;
};
const niceMax = (v) => { if (v <= 0) return 1; const p = 10 ** Math.floor(Math.log10(v)); const n = v / p; return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p; };
const compact = (n) => (n >= 1e6 ? (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M" : n >= 1e3 ? (n / 1e3).toFixed(n >= 1e4 ? 0 : 1).replace(/\.0$/, "") + "k" : String(Math.round(n)));

export const SERIES_COLORS = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)", "var(--s5)"];

function tipper(box) {
  const tip = h("div", { class: "tip hidden" }); box.append(tip);
  return {
    show(html, ev) {
      tip.innerHTML = html; tip.classList.remove("hidden");
      const r = box.getBoundingClientRect();
      let x = ev.clientX - r.left + 12; if (x > r.width - 190) x = ev.clientX - r.left - 190;
      tip.style.left = Math.max(4, x) + "px"; tip.style.top = Math.max(4, ev.clientY - r.top - 54) + "px";
    },
    hide() { tip.classList.add("hidden"); },
  };
}

export function stackedColumns({ title, note, buckets, series, format = compact, unitLabel = "" }) {
  const box = h("section", { class: "chart" });
  const W = 760, H = 240, L = 44, B = 28, T = 10, R = 8;
  const total = (b) => series.reduce((s, x) => s + (b.parts[x.key] || 0), 0);
  const max = niceMax(Math.max(0, ...buckets.map(total)));
  const bw = (W - L - R) / Math.max(1, buckets.length), gap = Math.min(10, bw * 0.25);
  const y = (v) => T + (H - T - B) * (1 - v / max);
  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${title}. ${note || ""}` });
  const ticks = String(max)[0] === "2" ? 4 : 5;
  for (let i = 0; i <= ticks; i++) {                 // recessive grid
    const v = (max / ticks) * i, yy = y(v);
    root.append(svg("line", { x1: L, x2: W - R, y1: yy, y2: yy, stroke: "var(--line)", "stroke-width": i ? 1 : 1.5 }));
    const t = svg("text", { x: L - 6, y: yy + 4, "text-anchor": "end", "font-size": 11, fill: "var(--muted)" }); t.textContent = format(v); root.append(t);
  }
  const tip = tipper(box), step = Math.ceil(buckets.length / 8);
  buckets.forEach((b, i) => {
    const x = L + i * bw + gap / 2, w = Math.max(2, bw - gap);
    let acc = 0;
    series.forEach((s) => {
      const v = b.parts[s.key] || 0; if (!v) return;
      const y1 = y(acc + v), y0 = y(acc); acc += v;
      root.append(svg("rect", { x, y: y1, width: w, height: Math.max(1, y0 - y1 - 2), rx: 2, fill: s.color }));   // 2px surface gap between segments
    });
    const hit = svg("rect", { x: L + i * bw, y: T, width: bw, height: H - T - B, fill: "transparent" });
    hit.addEventListener("pointermove", (ev) => tip.show(`<b>${b.label}</b><br>` + series.filter((s) => b.parts[s.key]).map((s) =>
      `<span style="color:${s.color}">&#9632;</span> ${s.label}: ${format(b.parts[s.key])}`).join("<br>") + (series.length > 1 ? `<br>Total: ${format(total(b))}` : ""), ev));
    hit.addEventListener("pointerleave", tip.hide); root.append(hit);
    if (i % step === 0) { const t = svg("text", { x: x + w / 2, y: H - 8, "text-anchor": "middle", "font-size": 11, fill: "var(--muted)" }); t.textContent = b.label; root.append(t); }
  });
  const legend = series.length > 1 ? h("div", { class: "legend" }, series.map((s) => h("span", null, h("i", { style: `background:${s.color}` }), s.label))) : null;
  const table = h("div", { class: "scroll hidden" }, h("table", null,
    h("thead", null, h("tr", null, h("th", null, ""), series.map((s) => h("th", { class: "num" }, s.label)), h("th", { class: "num" }, "Total"))),
    h("tbody", null, buckets.map((b) => h("tr", null, h("td", null, b.label), series.map((s) => h("td", { class: "num" }, format(b.parts[s.key] || 0))), h("td", { class: "num" }, format(total(b))))))));
  const toggle = h("button", { class: "ghost small", onclick: () => { const showT = table.classList.toggle("hidden"); root.classList.toggle("hidden", !showT); toggle.textContent = showT ? "Show as table" : "Show as chart"; } }, "Show as table");
  box.prepend(h("div", { class: "row between" }, h("div", null, h("h3", null, title), note ? h("div", { class: "muted small" }, note) : null), toggle));
  if (legend) box.append(legend);
  box.append(root, table);
  if (!buckets.length || !max) box.append(h("p", { class: "muted", style: "padding:1rem 0" }, "No model calls in this period yet."));
  return box;
}

export function rankedBars({ title, note, rows, format = compact }) {
  const box = h("section", { class: "chart" });
  const max = Math.max(1, ...rows.map((r) => r.value));
  box.append(h("h3", null, title), note ? h("div", { class: "muted small" }, note) : null);
  if (!rows.length) box.append(h("p", { class: "muted", style: "padding:.75rem 0" }, "Nothing to show yet."));
  const tip = tipper(box);
  rows.forEach((r) => {
    const row = h("div", { style: "display:grid;grid-template-columns:minmax(80px,28%) 1fr 64px;gap:.6rem;align-items:center;margin:.35rem 0" },
      h("span", { class: "small", style: "overflow:hidden;text-overflow:ellipsis;white-space:nowrap", title: r.label }, r.label),
      h("div", { style: "background:var(--sunk);border-radius:4px;height:14px" }, h("div", { style: `width:${Math.max(1.5, (r.value / max) * 100)}%;height:100%;background:var(--s1);border-radius:4px` })),
      h("span", { class: "small", style: "text-align:right;font-variant-numeric:tabular-nums" }, format(r.value)));
    row.addEventListener("pointermove", (ev) => r.tip && tip.show(r.tip, ev)); row.addEventListener("pointerleave", tip.hide);
    box.append(row);
  });
  return box;
}
