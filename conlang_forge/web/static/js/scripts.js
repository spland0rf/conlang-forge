// Writing systems: a list of the user's own, and an editor that regenerates live as dials change.
// A system can be "designed for" a language (its letters then cover that language's sounds exactly) and can be that
// language's primary writing system.
import { del, get, post, put } from "./api.js";
import { analyzeImage } from "./imagemeasure.js";
import { versionsPanel } from "./versions.js";
import { button, confirmBox, errorText, field, h, mount, toast } from "./ui.js";

const rnd = () => Math.floor(Math.random() * 2 ** 31);
const SOUND_DIALS = new Set(["consonants", "vowels"]);      // set by the language's own sounds when a system is designed for one

export async function scriptsPage(arg) {
  if (!arg) return listPage();
  const [id, q] = arg.split("?");
  const lang = new URLSearchParams(q || "").get("lang");
  if (id === "new") return listPage(lang);          // choosing how to make one now happens on the list page, before it is created
  return editorPage(id, lang);
}

// ------------------------------------------------------------------ the list + the create panel
const HOW = [["random", "Surprise me"], ["words", "From a description"], ["picture", "From a picture"]];
const TWEAK_GROUP = "Style";           // the settings offered up front; the editor has all the rest

async function listPage(presetLang) {
  const [{ scripts }, cat, langs] = await Promise.all([get("/api/scripts"), get("/api/script/dials"), get("/api/conlangs")]);
  const languages = langs.conlangs || [];
  const rows = scripts.length
    ? h("div", { class: "scr-list" }, scripts.map((s) => h("a", { class: "scr-item", href: `#/scripts/${s.id}` },
      h("strong", null, s.name),
      h("span", { class: "muted small" }, s.conlang_name ? `designed for ${s.conlang_name}` : "not tied to a language"),
      s.primary ? h("span", { class: "badge" }, "primary") : null)))
    : h("div", { class: "empty" }, h("span", { class: "word" }, "No writing systems yet"), "Create your first one on the right: describe the look, show a picture, or just press the button.");

  // ---- the create panel
  const msg = h("div", { "aria-live": "polite" });
  const name = h("input", { type: "text", maxlength: 80, placeholder: "Leave blank to name it for you" });
  const seed = h("input", { type: "text", inputmode: "numeric", placeholder: "Random" });
  const langSel = h("select", { "aria-label": "Designed for" }, h("option", { value: "" }, "No language (a free-standing script)"),
    languages.map((l) => h("option", { value: l.id, selected: l.id === presetLang }, l.name)));
  let how = "random";
  const words = h("textarea", { rows: 3, maxlength: 1500, "aria-label": "Describe the look you want",
    placeholder: "e.g. \"Lots of vertical and diagonal lines and slashes, with circles as diacritical marks. It should rise from a solid baseline.\"" });
  const file = h("input", { type: "file", accept: "image/png,image/jpeg,image/webp", "aria-label": "A picture of letters you like" });
  const wordsBox = h("div", { hidden: true }, words, h("p", { class: "muted small" }, "Your words are turned into settings, which you can review and change afterwards."));
  const pictureBox = h("div", { hidden: true }, file, h("p", { class: "muted small" },
    "Choose a picture of sample letters whose style you like. It is shrunk in your browser, read once, and not kept. The letters are not copied; the picture only steers the style settings."));
  const howBtns = HOW.map(([k, label]) => h("button", { type: "button", "aria-pressed": k === how ? "true" : "false", onclick: () => pickHow(k) }, label));
  function pickHow(k) {
    how = k;
    HOW.forEach(([key], i) => howBtns[i].setAttribute("aria-pressed", key === k ? "true" : "false"));
    wordsBox.hidden = k !== "words"; pictureBox.hidden = k !== "picture";
  }
  // a few style settings up front; anything left on "Surprise me" is chosen by the seed
  const tweaks = cat.dials.filter((d) => d.group === TWEAK_GROUP && !SOUND_DIALS.has(d.key)).map((d) => {
    let input, outEl = null, touched = false;
    if (d.type === "choice") {
      input = h("select", null, h("option", { value: "" }, "Surprise me"), d.values.map((v) => h("option", { value: v }, v)));
    } else {
      outEl = h("output", null, "Surprise me");
      input = h("input", { type: "range", min: d.min, max: d.max, step: d.step || 0.01, value: (d.min + d.max) / 2,
        oninput: () => { touched = true; outEl.textContent = Number(input.value).toFixed(2); } });
    }
    const reset = d.type === "choice" ? null : h("button", { type: "button", class: "small", onclick: () => { touched = false; outEl.textContent = "Surprise me"; } }, "Surprise me");
    return { d, root: h("label", { class: "scr-dial", title: d.description }, h("span", { class: "scr-name" }, d.label), input, outEl, reset),
      read: () => (d.type === "choice" ? (input.value || undefined) : (touched ? Number(input.value) : undefined)) };
  });
  const labelOf = (k) => (cat.dials.find((d) => d.key === k) || { label: k }).label;
  const box = h("section", { class: "forge", "aria-labelledby": "wh" });

  async function create() {
    msg.replaceChildren();
    const pins = {};
    for (const t of tweaks) { const v = t.read(); if (v !== undefined) pins[t.d.key] = v; }
    let seedN = rnd();
    if (seed.value.trim()) {
      if (!/^\d{1,10}$/.test(seed.value.trim())) { msg.replaceChildren(h("p", { class: "err", role: "alert" }, "The seed must be a whole number.")); return; }
      seedN = Number(seed.value.trim());
    }
    const keep = [...box.childNodes];
    mount(box, h("div", { class: "forging", role: "status" }, h("span", { class: "word" }, how === "random" ? "Designing…" : how === "words" ? "Reading your description…" : "Looking at the picture…"),
      h("span", { class: "spinner" })));
    const fail = (e) => { mount(box, ...keep); msg.replaceChildren(h("p", { class: "err", role: "alert" }, errorText(e))); };
    let applied = [];
    try {
      let r = null;
      if (how === "words") {
        if (!words.value.trim()) throw new Error("Write a few words about the look first.");
        r = await post("/api/scripts/interpret", { text: words.value });
      } else if (how === "picture") {
        const f = file.files && file.files[0];
        if (!f) throw new Error("Choose a picture first.");
        const { image, measures } = await analyzeImage(f);
        r = await post("/api/scripts/interpret-image", { image, measures });
      }
      if (r) {
        if (r.usage) window.dispatchEvent(new Event("cf:usage"));
        for (const p of r.proposals) if (!(p.key in pins)) { pins[p.key] = p.value; applied.push(p); }      // settings you chose above win
      }
      const made = await post("/api/scripts", { name: name.value.trim(), seed: seedN, pins, conlang_id: langSel.value || null });
      if (applied.length) toast(`Made from your ${how === "words" ? "description" : "picture"}: ${applied.map((p) => `${labelOf(p.key)} ${p.value}`).join(", ")}.`);
      location.hash = `#/scripts/${made.script_record.id}`;
    } catch (e) { fail(e); }
  }

  box.append(
    h("h2", { id: "wh" }, "Create a writing system"),
    h("p", { class: "muted small" }, "Choose how it should look. You can change any of it afterwards."),
    msg,
    h("div", { class: "seg", role: "group", "aria-label": "How to create it" }, howBtns),
    wordsBox, pictureBox,
    field("Name", name),
    field("Designed for", langSel),
    field("Seed", h("div", { class: "seedrow" }, seed, h("button", { type: "button", onclick: () => { seed.value = String(rnd()); } }, "Roll"))),
    h("details", { class: "dials" }, h("summary", null, "Shape the writing system (optional)"), tweaks.map((t) => t.root)),
    button("Create writing system", create, "primary"));
  return {
    title: "Writing systems",
    node: h("div", { class: "home" }, h("div", null, h("h1", null, "Your writing systems"),
      h("p", { class: "muted" }, "Design a script, tie it to a language so it has a letter for every sound, and set it as that language's primary script. Any script can also write any of your languages, using its closest sounds."),
      rows), box),
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

  // Chosen letter shapes the style could not give to most letters of their class (a ring needs round corners, for example)
  function shapeNotes() {
    const rep = (result.script && result.script.shape_report) || {};
    const weak = Object.entries(rep).filter(([, r]) => r.letters && r.wearing * 2 < r.letters);
    if (!weak.length) return null;
    return h("p", { class: "muted small scr-shape-note" }, weak.map(([g, r]) =>
      `Only ${r.wearing} of ${r.letters} ${g} letters could be drawn as a ${r.shape} in this style. Try other corners or a plainer style.`).join(" "));
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
          ? ` · similar shapes share sounds ${Math.round(m.sound_coherence.nearest_same_manner * 100)}%` : "")),
      shapeNotes());
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
    head, describeCard, bar, h("div", { class: "scr-layout" }, controls, out),
    rec ? h("details", { class: "scr-card", style: "margin-top:1rem" }, h("summary", null, h("strong", null, "Versions")),
      versionsPanel({ kind: "script", id: rec.id, prepare: async () => (dirty ? await save() : true) })) : null);
  return { node, title: "Writing systems", wide: true };
}
