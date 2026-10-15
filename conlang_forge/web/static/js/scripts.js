// Writing systems: a list of the user's own, and an editor that regenerates live as dials change.
// A system can be "designed for" a language (its letters then cover that language's sounds exactly) and can be that
// language's primary writing system.
import { del, get, post, put } from "./api.js";
import { analyzeImage } from "./imagemeasure.js";
import { button, confirmBox, h, mount, toast, errorText } from "./ui.js";

const rnd = () => Math.floor(Math.random() * 2 ** 31);
const SOUND_DIALS = new Set(["consonants", "vowels"]);      // set by the language's own sounds when a system is designed for one

export async function scriptsPage(arg) {
  if (!arg) return listPage();
  const [id, q] = arg.split("?");
  const lang = new URLSearchParams(q || "").get("lang");
  return editorPage(id === "new" ? null : id, lang);
}

// ------------------------------------------------------------------ the list
async function listPage() {
  const { scripts } = await get("/api/scripts");
  const rows = scripts.length
    ? h("div", { class: "scr-list" }, scripts.map((s) => h("a", { class: "scr-item", href: `#/scripts/${s.id}` },
      h("strong", null, s.name),
      h("span", { class: "muted small" }, s.conlang_name ? `designed for ${s.conlang_name}` : "not tied to a language"),
      s.primary ? h("span", { class: "badge" }, "primary") : null)))
    : h("p", { class: "muted" }, "You have not saved a writing system yet. Create one, then link it to a language as its own script.");
  return {
    title: "Writing systems",
    node: h("div", null, h("h1", null, "Writing systems"),
      h("p", { class: "muted" }, "Design a script, tie it to a language so it has a letter for every sound, and set it as that language's primary script. Any script can also write any of your languages, using its closest sounds."),
      h("div", { class: "row", style: "margin:.8rem 0 1.2rem" }, h("a", { class: "btn primary", href: "#/scripts/new" }, "New writing system")),
      rows),
  };
}

// ------------------------------------------------------------------ the editor
async function editorPage(id, presetLang) {
  const [cat, langs, saved] = await Promise.all([get("/api/script/dials"), get("/api/conlangs"),
    id ? get(`/api/scripts/${id}`) : Promise.resolve(null)]);
  const languages = langs.conlangs || [];
  let rec = saved ? saved.script_record : null;
  let name = rec ? rec.name : "";
  let conlang = rec ? rec.conlang_id || "" : (presetLang && languages.some((l) => l.id === presetLang) ? presetLang : "");
  const pins = rec ? { ...rec.pins } : {};
  let seed = rec ? rec.seed : rnd();
  let result = saved, busy = 0, dirty = !rec;

  const out = h("div", { class: "scr-out" });
  const status = h("span", { class: "muted small" });
  const seedIn = h("input", { type: "number", min: 0, max: 2 ** 31 - 1, value: seed, "aria-label": "Seed",
    onchange: () => { seed = Math.max(0, Math.floor(Number(seedIn.value) || 0)); touch(); run(); } });
  const nameIn = h("input", { type: "text", maxlength: 80, value: name, placeholder: "Name this writing system", "aria-label": "Name",
    oninput: () => { name = nameIn.value; touch(); } });
  const langSel = h("select", { "aria-label": "Designed for", onchange: () => { conlang = langSel.value; touch(); run(); } },
    h("option", { value: "" }, "No language (a free-standing script)"),
    languages.map((l) => h("option", { value: l.id, selected: l.id === conlang }, l.name)));
  const controls = h("div", { class: "scr-controls" });
  const primaryBtn = button("Make primary for this language", setPrimary);
  const delBtn = rec ? button("Delete", removeIt, "danger") : null;

  function touch() { dirty = true; renderStatus(); }
  function renderStatus() {
    status.textContent = !rec ? "Not saved yet" : dirty ? "Unsaved changes" : "Saved";
    primaryBtn.hidden = !conlang;
    const isPrimary = !!(rec && rec.primary && rec.conlang_id === conlang);
    primaryBtn.disabled = isPrimary && !dirty;
    primaryBtn.textContent = isPrimary ? "Primary for this language" : "Make primary for this language";
  }

  async function run() {
    const mine = ++busy;
    out.classList.add("loading");
    try {
      const r = await post("/api/scripts/preview", { seed, pins, conlang_id: conlang || null });
      if (mine !== busy) return;
      result = r; seedIn.value = seed; draw();
    } catch (e) { if (mine === busy) toast(errorText(e), true); }
    finally { if (mine === busy) out.classList.remove("loading"); }
  }

  function draw() {
    const m = result.metrics || {};
    mount(out,
      result.sentences && result.sentences.length ? h("div", { class: "scr-card" }, h("h3", null, `Sentences in ${result.language.name}`),
        result.sentences.map((s) => h("div", { class: "scr-sentence" }, h("div", { class: "scr-svg", html: s.svg }),
          h("div", { class: "muted small" }, s.english)))) : null,
      h("div", { class: "scr-card" }, h("h3", null, "Sample text"), h("div", { class: "scr-svg", html: result.sample }),
        conlang ? null : h("p", { class: "muted small" }, "Invented words. Choose a language above to see its own sentences.")),
      h("div", { class: "scr-card" }, h("h3", null, "Letters"), h("div", { class: "scr-svg", html: result.specimen })),
      h("p", { class: "muted small" }, `${m.letters ?? "?"} letters`
        + (m.sound_coherence && m.sound_coherence.nearest_same_manner != null
          ? ` · similar shapes share sounds ${Math.round(m.sound_coherence.nearest_same_manner * 100)}%` : "")));
    syncControls();
    renderStatus();
  }

  const widgets = {};
  const fmt = (d, v) => (d.step && d.step < 1 ? Number(v).toFixed(2) : String(v));
  function syncControls() {
    for (const d of cat.dials) {
      const w = widgets[d.key], pinned = d.key in pins, val = result.spec[d.key];
      const fixed = !!conlang && SOUND_DIALS.has(d.key);
      w.root.classList.toggle("pinned", pinned && !fixed);
      w.pin.checked = pinned && !fixed;
      w.pin.disabled = w.input.disabled = fixed;
      w.root.title = fixed ? "Set by the language's own sounds" : d.description;
      if (d.type === "choice") w.input.value = String(val);
      else { w.input.value = val; w.out.textContent = fmt(d, val) + (fixed ? " (from the language)" : ""); }
    }
  }

  function control(d) {
    const read = () => (d.type === "choice" ? input.value : Number(input.value));
    const pin = h("input", { type: "checkbox", title: "Keep this setting when the seed changes", "aria-label": `Keep ${d.label}`,
      onchange: () => { if (pin.checked) pins[d.key] = read(); else delete pins[d.key]; touch(); run(); } });
    let input, outEl = null;
    if (d.type === "choice") {
      input = h("select", { onchange: () => { pins[d.key] = input.value; touch(); run(); } }, d.values.map((v) => h("option", { value: v }, v)));
    } else {
      outEl = h("output", null, "");
      input = h("input", { type: "range", min: d.min, max: d.max, step: d.step || 0.01,
        oninput: () => { outEl.textContent = fmt(d, input.value); },
        onchange: () => { pins[d.key] = Number(input.value); touch(); run(); } });
    }
    const root = h("label", { class: "scr-dial", title: d.description }, h("span", { class: "scr-name" }, d.label), input, outEl, pin);
    widgets[d.key] = { root, input, pin, out: outEl };
    return root;
  }
  for (const g of cat.groups) {
    const ds = cat.dials.filter((d) => d.group === g);
    if (ds.length) controls.append(h("fieldset", { class: "scr-group" }, h("legend", null, g), ds.map(control)));
  }

  async function save() {
    const body = { name: name.trim(), seed, pins, conlang_id: conlang || null };
    try {
      const r = rec ? await put(`/api/scripts/${rec.id}`, body) : await post("/api/scripts", body);
      toast("Saved.");
      if (!rec) { location.hash = `#/scripts/${r.script_record.id}`; return true; }
      rec = r.script_record; result = r; dirty = false; name = rec.name; nameIn.value = name; draw();
      return true;
    } catch (e) { toast(errorText(e), true); return false; }
  }
  async function setPrimary() {
    try {
      if ((dirty || !rec || rec.conlang_id !== conlang) && !(await save())) return;
      const r = await put(`/api/conlangs/${conlang}/primary-script`, { script_id: rec.id });
      rec = r.script_record; toast("This is now the primary writing system."); renderStatus();
    } catch (e) { toast(errorText(e), true); }
  }
  async function removeIt() {
    if (!(await confirmBox("Delete this writing system?", "Languages written in it will fall back to a newly designed primary script.", "Delete", true))) return;
    try { await del(`/api/scripts/${rec.id}`); location.hash = "#/scripts"; } catch (e) { toast(errorText(e), true); }
  }

  // design by description: words in, suggested dial settings out; the user ticks what to apply
  const describeIn = h("textarea", { rows: 3, maxlength: 1500, "aria-label": "Describe the look you want",
    placeholder: "Describe the look, e.g. \"Lots of vertical and diagonal lines and slashes, with circles as diacritical marks. It should rise from a solid baseline.\"" });
  const suggestions = h("div", { "aria-live": "polite" });
  const labelOf = (k) => (cat.dials.find((d) => d.key === k) || { label: k }).label;
  function showProposals(r) {
    if (r.usage) window.dispatchEvent(new Event("cf:usage"));
    const boxes = r.proposals.map((p) => {
      const cb = h("input", { type: "checkbox", checked: true, "aria-label": `Apply ${labelOf(p.key)}` });
      return { p, cb, row: h("li", null, h("label", null, cb, " ", h("strong", null, labelOf(p.key)), ": ", String(p.value),
        p.evidence ? h("span", { class: "muted small" }, ` — “${p.evidence}”`) : null)) };
    });
    mount(suggestions,
      boxes.length ? h("div", null, h("ul", { class: "scr-suggest" }, boxes.map((b) => b.row)),
        button("Apply selected", async () => {
          for (const b of boxes) if (b.cb.checked) pins[b.p.key] = b.p.value;
          touch(); mount(suggestions); await run();
        }, "primary small")) : null,
      r.notes.map((n) => h("p", { class: "muted small" }, n)));
  }
  async function suggest() {
    if (!describeIn.value.trim()) { toast("Write a few words about the look first.", true); return; }
    mount(suggestions, h("p", { class: "muted" }, h("span", { class: "spinner" }), " Reading your description…"));
    try { showProposals(await post("/api/scripts/interpret", { text: describeIn.value })); }
    catch (e) { mount(suggestions, h("p", { class: "error", role: "alert" }, errorText(e))); }
  }
  const fileIn = h("input", { type: "file", accept: "image/png,image/jpeg,image/webp", "aria-label": "A picture of letters you like" });
  const thumb = h("img", { class: "scr-thumb", alt: "", hidden: true });
  async function suggestFromImage() {
    const f = fileIn.files && fileIn.files[0];
    if (!f) { toast("Choose a picture first.", true); return; }
    mount(suggestions, h("p", { class: "muted" }, h("span", { class: "spinner" }), " Looking at the picture…"));
    try {
      const { image, measures } = await analyzeImage(f);
      thumb.src = URL.createObjectURL(f); thumb.hidden = false;
      showProposals(await post("/api/scripts/interpret-image", { image, measures }));
    } catch (e) { mount(suggestions, h("p", { class: "error", role: "alert" }, errorText(e))); }
  }
  const describeCard = h("div", { class: "scr-card" }, h("h3", null, "Describe the look"),
    describeIn, h("div", { class: "row", style: "margin:.4rem 0" }, button("Suggest settings", suggest)),
    h("h3", { style: "margin-top:.8rem" }, "Or show a picture"),
    h("p", { class: "muted small" }, "Upload a picture of sample letters whose style you like. It is shrunk in your browser, read once, and not kept. The letters are not copied; the picture only steers the style settings."),
    h("div", { class: "row", style: "margin:.4rem 0" }, fileIn, button("Suggest from picture", suggestFromImage), thumb), suggestions);

  const bar = h("div", { class: "row scr-bar" },
    h("label", { class: "scr-seed" }, "Seed ", seedIn),
    h("button", { class: "primary", onclick: () => { seed = rnd(); touch(); run(); } }, "Randomize"),
    h("button", { title: "Keep every dial at its current value, so Randomize only changes the small details", onclick: () => {
      for (const d of cat.dials) if (!(conlang && SOUND_DIALS.has(d.key))) pins[d.key] = result.spec[d.key];
      touch(); syncControls();
    } }, "Keep all settings"),
    h("button", { onclick: () => { for (const k in pins) delete pins[k]; touch(); run(); } }, "Release all"));
  const head = h("div", { class: "scr-head" },
    h("label", null, "Name ", nameIn), h("label", null, "Designed for ", langSel),
    h("div", { class: "row" }, button("Save", save, "primary"), primaryBtn, delBtn, status));

  if (result) draw(); else await run();
  renderStatus();
  const node = h("div", null, h("div", null, h("a", { href: "#/scripts", class: "small" }, "All writing systems")),
    h("h1", null, rec ? rec.name : "New writing system"),
    h("p", { class: "muted" }, "Tick the box beside a setting to keep it: Randomize then changes everything except the kept settings. Moving a slider keeps that setting automatically, and you can always keep editing. Nothing is stored until you press Save. Tying the system to a language gives it a letter for each of that language's sounds."),
    head, describeCard, bar, h("div", { class: "scr-layout" }, controls, out));
  return { node, title: "Writing systems", wide: true };
}
