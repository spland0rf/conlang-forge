// Writing systems: generate a script from a seed, pin the dials you care about, randomize the rest.
import { get, post } from "./api.js";
import { h, mount, toast, errorText } from "./ui.js";

const rnd = () => Math.floor(Math.random() * 2 ** 31);

export async function scriptsPage() {
  const cat = await get("/api/script/dials");
  const pins = {};            // dial key -> pinned value; everything else is left to the seed
  let seed = rnd(), result = null, busy = 0;

  const out = h("div", { class: "scr-out" });
  const seedIn = h("input", { type: "number", min: 0, max: 2 ** 31 - 1, value: seed, "aria-label": "Seed",
    onchange: () => { seed = Math.max(0, Math.floor(Number(seedIn.value) || 0)); run(); } });
  const controls = h("div", { class: "scr-controls" });

  async function run() {
    const mine = ++busy;
    out.classList.add("loading");
    try {
      const r = await post("/api/script/generate", { seed, pins });
      if (mine !== busy) return;
      result = r; seedIn.value = seed; draw();
    } catch (e) { if (mine === busy) toast(errorText(e), true); }
    finally { if (mine === busy) out.classList.remove("loading"); }
  }

  function draw() {
    const m = result.metrics || {};
    mount(out,
      h("div", { class: "scr-card" }, h("h3", null, "Sample text"), h("div", { class: "scr-svg", html: result.sample })),
      h("div", { class: "scr-card" }, h("h3", null, "Letters"), h("div", { class: "scr-svg", html: result.specimen })),
      h("p", { class: "muted small" }, `${m.letters ?? "?"} letters`
        + (m.sound_coherence && m.sound_coherence.nearest_same_manner != null
          ? ` · similar shapes share sounds ${Math.round(m.sound_coherence.nearest_same_manner * 100)}%` : "")));
    syncControls();
  }

  const widgets = {};
  function syncControls() {
    for (const d of cat.dials) {
      const w = widgets[d.key], pinned = d.key in pins, val = result.spec[d.key];
      w.root.classList.toggle("pinned", pinned);
      w.pin.checked = pinned;
      if (d.type === "choice") w.input.value = String(val);
      else { w.input.value = val; w.out.textContent = fmt(d, val); }
    }
  }
  const fmt = (d, v) => (d.step && d.step < 1 ? Number(v).toFixed(2) : String(v));

  function control(d) {
    const pin = h("input", { type: "checkbox", title: "Lock this value", "aria-label": `Lock ${d.label}`,
      onchange: () => { if (pin.checked) pins[d.key] = read(); else delete pins[d.key]; run(); } });
    let input, outEl = null;
    const read = () => d.type === "choice" ? input.value : Number(input.value);
    if (d.type === "choice") {
      input = h("select", { onchange: () => { pins[d.key] = input.value; run(); } },
        d.values.map((v) => h("option", { value: v }, v)));
    } else {
      outEl = h("output", null, "");
      input = h("input", { type: "range", min: d.min, max: d.max, step: d.step || 0.01,
        oninput: () => { outEl.textContent = fmt(d, input.value); },
        onchange: () => { pins[d.key] = Number(input.value); run(); } });
    }
    const root = h("label", { class: "scr-dial", title: d.description },
      h("span", { class: "scr-name" }, d.label), input, outEl, pin);
    widgets[d.key] = { root, input, pin, out: outEl };
    return root;
  }

  for (const g of cat.groups) {
    const ds = cat.dials.filter((d) => d.group === g);
    if (ds.length) controls.append(h("fieldset", { class: "scr-group" }, h("legend", null, g), ds.map(control)));
  }

  const bar = h("div", { class: "row scr-bar" },
    h("label", { class: "scr-seed" }, "Seed ", seedIn),
    h("button", { class: "primary", onclick: () => { seed = rnd(); run(); } }, "Randomize"),
    h("button", { onclick: () => { for (const k in pins) delete pins[k]; run(); } }, "Unlock all"));

  await run();
  const node = h("div", null,
    h("h1", null, "Writing systems"),
    h("p", { class: "muted" }, "Pick a seed or randomize. Lock a dial to keep it fixed while the seed changes everything else."),
    bar, h("div", { class: "scr-layout" }, controls, out));
  return { node, title: "Writing systems", wide: true };
}
