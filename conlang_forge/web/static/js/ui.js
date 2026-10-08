// Small DOM helpers (no framework).
export function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = v;
    else if (k === "value") el.value = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  add(el, kids);
  return el;
}
function add(el, kids) {
  for (const k of kids.flat(Infinity)) {
    if (k == null || k === false) continue;
    el.append(k.nodeType ? k : document.createTextNode(String(k)));
  }
}
export const $ = (sel, root = document) => root.querySelector(sel);
export function mount(el, ...kids) { el.replaceChildren(); add(el, kids); return el; }

export function toast(msg, bad = false) {
  const t = h("div", { class: "toast" + (bad ? " bad" : "") }, msg);
  document.getElementById("toasts").append(t);
  setTimeout(() => t.remove(), bad ? 6000 : 3200);
}
export function errorText(e) {
  if (e && e.detail && e.detail.resets_at && e.status === 429) {
    const mins = Math.max(1, Math.round((e.detail.resets_at - Date.now()) / 60000));
    return `${e.message} Try again in about ${mins < 90 ? mins + " minutes" : Math.round(mins / 60) + " hours"}.`;
  }
  return (e && e.message) || "Something went wrong.";
}

export function modal(title, bodyEl, actions) {
  const back = h("div", { class: "modal-back", onclick: (e) => e.target === back && close() },
    h("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": title },
      h("h2", null, title), bodyEl, h("div", { class: "row end", style: "margin-top:1rem" }, actions(close))));
  function close() { back.remove(); document.removeEventListener("keydown", esc); }
  const esc = (e) => e.key === "Escape" && close();
  document.addEventListener("keydown", esc);
  document.body.append(back);
  const first = back.querySelector("input,select,textarea,button.primary"); first && first.focus();
  return close;
}
export function confirmBox(title, message, okLabel, danger = false) {
  return new Promise((res) => {
    modal(title, h("p", null, message), (close) => [
      h("button", { onclick: () => { close(); res(false); } }, "Cancel"),
      h("button", { class: danger ? "danger" : "primary", onclick: () => { close(); res(true); } }, okLabel)]);
  });
}
export function drawer(contentEl) {
  const back = h("div", { class: "drawer-back", onclick: (e) => e.target === back && close() },
    h("aside", { class: "drawer", role: "dialog", "aria-modal": "true" }, contentEl));
  function close() { back.remove(); document.removeEventListener("keydown", esc); }
  const esc = (e) => e.key === "Escape" && close();
  document.addEventListener("keydown", esc);
  document.body.append(back);
  return close;
}

export const nf = new Intl.NumberFormat();
export function fmtTokens(n) { return n == null ? "no limit" : n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M" : n >= 1e4 ? Math.round(n / 1e3) + "k" : nf.format(n); }
export function fmtUsd(micro) { const d = micro / 1e6; return d < 0.01 && micro > 0 ? "<$0.01" : "$" + d.toFixed(d < 10 ? 2 : 0); }
export function ago(ms) {
  if (!ms) return "never";
  const s = (Date.now() - ms) / 1000;
  if (s < 90) return "just now"; if (s < 5400) return Math.round(s / 60) + " min ago";
  if (s < 129600) return Math.round(s / 3600) + " h ago"; if (s < 86400 * 40) return Math.round(s / 86400) + " days ago";
  return new Date(ms).toLocaleDateString();
}
export function when(ms) { return ms ? new Date(ms).toLocaleString() : "never"; }

export function meter(used, limit, label) {
  const pct = limit == null ? 0 : Math.min(100, (used / Math.max(1, limit)) * 100);
  const cls = pct >= 100 ? "meter full" : pct >= 80 ? "meter hot" : "meter";
  return h("div", { title: label }, h("div", { class: cls, role: "meter", "aria-valuenow": used, "aria-valuemin": 0, "aria-valuemax": limit ?? used, "aria-label": label },
    h("i", { style: `width:${limit == null ? 0 : pct}%` })));
}
export function button(label, onclick, cls = "") {
  const b = h("button", { class: cls, onclick: async (e) => {
    b.disabled = true;
    try { await onclick(e); } finally { b.disabled = false; }
  } }, label);
  return b;
}
export function field(label, input, hint) {
  const id = "f" + Math.random().toString(36).slice(2, 8);
  input.id = id;
  return h("div", { class: "field" }, h("label", { for: id }, label), input, hint ? h("div", { class: "hint" }, hint) : null);
}
