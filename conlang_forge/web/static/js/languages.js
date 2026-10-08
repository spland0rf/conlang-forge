import { del, download, get, patch, post, text } from "./api.js";
import { renderMarkdown } from "./md.js";
import { translateTab } from "./translate.js";
import { state } from "./state.js";
import { getScript, setScript, sq } from "./script.js";
import { settingsTab } from "./settings.js";
import { ago, button, confirmBox, errorText, field, h, modal, mount, toast } from "./ui.js";

const TYPES = { isolating: "Isolating: short words, little endings", agglutinative: "Agglutinative: endings stack on words",
  fusional: "Fusional: endings blend and carry several meanings", polysynthetic: "Polysynthetic: long words carry whole sentences" };
const ORDERS = { SOV: "Subject, object, verb (like Japanese)", SVO: "Subject, verb, object (like English)", VSO: "Verb, subject, object (like Welsh)",
  VOS: "Verb, object, subject", OVS: "Object, verb, subject", OSV: "Object, subject, verb" };
const list = (a) => (a && a.length ? a.join(", ") : "none");

// ------------------------------------------------------------------ the list + the forge
export async function languagesPage() {
  const { conlangs } = await get("/api/conlangs");
  const me = state.me, cap = me.usage ? null : null;
  const name = h("input", { type: "text", maxlength: 40, placeholder: "Leave blank to invent one" });
  const seed = h("input", { type: "text", inputmode: "numeric", placeholder: "Random" });
  const sel = (key, label, options, fmt) => {
    const s = h("select", { "data-key": key }, h("option", { value: "" }, "Surprise me"), options.map((o) => h("option", { value: o }, fmt ? fmt(o) : o)));
    return field(label, s);
  };
  const D = state.config.dials;
  const dials = [
    sel("morphology.typology", "How words are built", D["morphology.typology"], (o) => TYPES[o] || o),
    sel("syntax.word_order", "Sentence order", D["syntax.word_order"], (o) => `${o}: ${ORDERS[o]}`),
    sel("syntax.adjective_order", "Adjectives", D["syntax.adjective_order"], (o) => (o === "adjective-noun" ? "Before the noun" : "After the noun")),
    sel("phonology.stress", "Stress", D["phonology.stress"], (o) => (o === "none" ? "Even, no stress" : "On the " + o + " syllable")),
    sel("morphology.numeral_base", "Counting base", D["morphology.numeral_base"], (o) => ({ 10: "10 (like English)", 12: "12 (dozens)", 20: "20 (scores)", 5: "5 (one hand)", 8: "8" }[o])),
  ];
  const msg = h("div");
  const forgeBox = h("section", { class: "forge", "aria-labelledby": "fh" });
  async function forge() {
    msg.replaceChildren();
    const pins = {};
    dials.forEach((f) => { const s = f.querySelector("select"); if (s.value) pins[s.dataset.key] = /^\d+$/.test(s.value) ? Number(s.value) : s.value; });
    const body = { name: name.value.trim(), pins };
    if (seed.value.trim()) { if (!/^\d{1,10}$/.test(seed.value.trim())) { msg.replaceChildren(h("p", { class: "err", role: "alert" }, "The seed must be a whole number.")); return; } body.seed = Number(seed.value.trim()); }
    const keep = [...forgeBox.childNodes];
    mount(forgeBox, h("div", { class: "forging", role: "status" }, h("span", { class: "word" }, "Forging…"), h("span", { class: "spinner" }),
      h("p", { class: "muted", style: "margin-top:.75rem" }, "Choosing sounds, building roots and writing 2,000 words. This takes a few seconds.")));
    try {
      const c = await post("/api/conlangs", body);
      location.hash = "#/lang/" + c.id;
    } catch (e) {
      mount(forgeBox, ...keep); msg.replaceChildren(h("p", { class: "err", role: "alert" }, errorText(e)));
    }
  }
  const sample = h("textarea", { rows: 4, maxlength: 20000, "aria-label": "Sample text", placeholder: "Paste words or sentences that sound the way you want, one per line. Add a meaning after a | if you like." });
  const modelOn = !!state.config.model_available;
  const readGrammar = h("input", { type: "checkbox", checked: modelOn, disabled: !modelOn || null });
  async function forgeFromSample() {
    msg.replaceChildren();
    const texts = sample.value.split("\n").map((t) => t.trim()).filter(Boolean);
    if (!texts.length) { msg.replaceChildren(h("p", { class: "err", role: "alert" }, "Paste some sample text first.")); return; }
    const pins = {};
    dials.forEach((f) => { const s2 = f.querySelector("select"); if (s2.value) pins[s2.dataset.key] = /^\d+$/.test(s2.value) ? Number(s2.value) : s2.value; });
    const body = { texts, pins, name: name.value.trim(), use_model: readGrammar.checked && modelOn };
    if (seed.value.trim() && /^\d{1,10}$/.test(seed.value.trim())) body.seed = Number(seed.value.trim());
    const keep = [...forgeBox.childNodes];
    mount(forgeBox, h("div", { class: "forging", role: "status" }, h("span", { class: "word" }, "Reading your sample…"), h("span", { class: "spinner" }),
      h("p", { class: "muted", style: "margin-top:.75rem" }, "Working out the sounds and grammar, then building the language.")));
    try {
      const c = await post("/api/conlangs/from-sample", body);
      window.dispatchEvent(new Event("cf:usage"));
      showShaped(c);
    } catch (e) { mount(forgeBox, ...keep); msg.replaceChildren(h("p", { class: "err", role: "alert" }, errorText(e))); }
  }
  function showShaped(c) {
    const sh = c.shaped, go = () => { location.hash = "#/lang/" + c.id; };
    const li = (p) => h("li", null, h("b", null, p.label + ": "), p.proposed_show, h("div", { class: "small muted" }, p.evidence));
    modal("Your language is ready", h("div", null,
      sh.applied.length ? [h("p", null, `The sample decided ${sh.applied.length} setting${sh.applied.length === 1 ? "" : "s"}:`), h("ul", { class: "shaped" }, sh.applied.map(li))]
        : h("p", null, "The sample was too short to decide anything, so the language was made at random."),
      sh.kept.length ? [h("p", null, "The sample suggested these, but you had fixed them, so your choice stands:"), h("ul", { class: "shaped" }, sh.kept.map((p) => h("li", null, h("b", null, p.label + ": "), "kept ", p.current_show, " (sample suggested ", p.proposed_show, ")")))] : null,
      h("p", { class: "muted" }, "Everything else was chosen at random, as usual. You can change any of it in the Settings tab."),
      sh.notes.map((n) => h("p", { class: "small muted" }, n))),
      (close) => [h("button", { class: "primary", onclick: () => { close(); go(); } }, "Open " + c.name)]);
    go();
  }
  forgeBox.append(
    h("h2", { id: "fh" }, "Forge a new language"),
    h("p", { class: "muted small" }, "Same seed and settings always give the same language."),
    msg, field("Name", name),
    field("Seed", h("div", { class: "seedrow" }, seed, h("button", { type: "button", onclick: () => { seed.value = String(Math.floor(Math.random() * 2 ** 31)); } }, "Roll"))),
    h("details", { class: "dials" }, h("summary", null, "Shape the language (optional)"), dials),
    button("Forge language", forge, "primary"),
    h("details", { class: "dials sampled" }, h("summary", null, "Or start from a sample"),
      h("p", { class: "muted small" }, "The sounds and grammar are worked out from your text. Anything you fixed above stays as you set it; whatever the sample cannot tell is chosen at random."),
      sample, h("label", { class: "check small muted", style: "margin:.5rem 0" }, readGrammar, " Also read the grammar (uses the model)"),
      button("Forge from sample", forgeFromSample, "primary")));
  const rows = conlangs.length ? h("ul", { class: "langlist" }, conlangs.map((c) =>
    h("li", null, h("a", { href: "#/lang/" + c.id },
      h("span", { class: "nm" }, c.name),
      h("span", { class: "when" }, ago(c.updated_at)),
      h("span", { class: "meta" }, [c.word_order, c.typology, "seed " + c.seed].filter(Boolean).join(" · ")))))) :
    h("div", { class: "empty" }, h("span", { class: "word" }, "No languages yet"), "Forge your first one on the right. Pick a few settings or just press the button.");
  return { title: "Languages", node: h("div", { class: "home" }, h("div", null, h("h1", null, "Your languages"), rows), forgeBox) };
}

// ------------------------------------------------------------------ one language
const cache = {};
export async function langPage(id, tab) {
  const lang = await get("/api/conlangs/" + id + sq());
  const p = lang.profile;
  const tabs = [["overview", "Overview"], ["translate", "Translate"], ["settings", "Settings"], ["dictionary", "Dictionary"], ["book", "Grammar book"], ["files", "Downloads"]];
  const body = h("div");
  const node = h("div", null,
    h("div", { class: "lhead" }, h("div", null, h("a", { href: "#/", class: "small" }, "All languages")),
      h("h1", { class: "word" }, lang.name), h("div", { class: "muted" }, `${p.words.toLocaleString()} words · ${p.grammar.word_order} · ${p.grammar.type} · seed ${p.seed}`),
      h("div", { class: "seg small", role: "group", "aria-label": "Letters used to write the language", title: "Only changes how words are drawn. The language itself does not change." },
        ["plain", "special"].map((m) => h("button", { class: getScript() === m ? "on" : "", "aria-pressed": String(getScript() === m), onclick: () => { setScript(m); window.dispatchEvent(new Event("hashchange")); } },
          m === "plain" ? "Plain letters" : "Special letters")))),
    h("nav", { class: "tabs", "aria-label": "Language sections" }, tabs.map(([k, label]) => h("a", { href: `#/lang/${id}/${k === "overview" ? "" : k}`, "aria-current": k === tab ? "page" : null }, label))),
    body);
  if (tab === "translate") body.append(translateTab(id, lang));
  else if (tab === "settings") body.append(await settingsTab(id, lang));
  else if (tab === "dictionary") body.append(await dictionaryTab(id, lang));
  else if (tab === "book") body.append(await bookTab(id, lang));
  else if (tab === "files") body.append(filesTab(id, lang));
  else body.append(overviewTab(id, lang));
  return { title: lang.name, node };
}

function overviewTab(id, lang) {
  const p = lang.profile, g = p.grammar, s = p.sounds;
  const fact = (k, v) => [h("dt", null, k), h("dd", null, v)];
  const q = { particle: "a question word", "verb inversion": "swapping the verb and subject", intonation: "tone of voice", "verbal affix": "an ending on the verb" }[g.questions] || g.questions;
  return h("div", { class: "cols" },
    h("section", null, h("h2", null, "Sounds"),
      h("p", { class: "small muted" }, "Consonants"), h("div", { class: "letters" }, s.consonants.map((c) => h("span", null, c))),
      h("p", { class: "small muted" }, "Vowels"), h("div", { class: "letters v" }, s.vowels.map((c) => h("span", null, c))),
      h("p", { class: "small muted" }, `Stress is ${s.stress === "none" ? "even" : "on the " + s.stress + " syllable"}. About ${Math.round(p.one_syllable_share * 100)}% of words have one syllable.`),
      h("h2", { style: "margin-top:2rem" }, "A few words"),
      h("table", null, h("tbody", null, p.quick_words.map((w) => h("tr", null, h("td", null, w.en), h("td", { class: "word", style: "font-size:1.25rem" }, w.form), h("td", { class: "word muted" }, w.ipa)))))),
    h("section", null, h("h2", null, "Grammar at a glance"),
      h("dl", { class: "facts" }, fact("Word building", g.type), fact("Sentence order", g.word_order), fact("Adjectives", g.adjectives),
        fact("Small words", g.adposition + "s"), fact("Number", ["singular", ...g.number].join(", ")), fact("Cases", list(g.cases)),
        fact("Genders", list(g.genders)), fact("Articles", g.definiteness), fact("Tenses", list(g.tenses)), fact("Verbs agree with", g.agreement === "none" ? "nothing" : g.agreement),
        fact("Yes/no questions", q), fact("Counting base", g.numeral_base)),
      h("p", { style: "margin-top:1.5rem" }, h("a", { class: "btn primary", href: `#/lang/${id}/book` }, "Start the grammar book")),
      h("div", { class: "row", style: "margin-top:2rem" },
        button("Rename", () => rename(id, lang), "small"), button("Delete", () => remove(id, lang), "small danger"))));
}

async function rename(id, lang) {
  const input = h("input", { type: "text", value: lang.name, maxlength: 80 });
  modal("Rename language", field("Name", input), (close) => [h("button", { onclick: close }, "Cancel"),
    h("button", { class: "primary", onclick: async () => { try { await patch("/api/conlangs/" + id, { name: input.value }); close(); toast("Renamed"); window.dispatchEvent(new Event("hashchange")); } catch (e) { toast(errorText(e), true); } } }, "Rename")]);
}
async function remove(id, lang) {
  if (!(await confirmBox("Delete " + lang.name + "?", "The language and its dictionary will be removed from your account. This cannot be undone.", "Delete language", true))) return;
  try { await del("/api/conlangs/" + id); toast("Deleted"); location.hash = "#/"; } catch (e) { toast(errorText(e), true); }
}

// ------------------------------------------------------------------ dictionary
function alphabetOrder(sounds) {
  const plain = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "");
  const letters = [...new Set([...sounds.consonants, ...sounds.vowels])];
  letters.sort((a, b) => (plain(a)[0] < plain(b)[0] ? -1 : plain(a)[0] > plain(b)[0] ? 1 : 0) || (a.length > 1) - (b.length > 1) || (plain(a) < plain(b) ? -1 : plain(a) > plain(b) ? 1 : 0) || ((a !== plain(a)) - (b !== plain(b))));
  const byLen = [...letters].sort((a, b) => b.length - a.length), idx = Object.fromEntries(letters.map((l, i) => [l, i]));
  const tokens = (w) => { const out = []; w = w.toLowerCase(); for (let i = 0; i < w.length;) { const t = byLen.find((l) => w.startsWith(l, i)) || w[i]; out.push(t); i += t.length; } return out; };
  return { tokens, key: (w) => tokens(w).map((t) => idx[t] ?? 999), letters };
}
const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

async function dictionaryTab(id, lang) {
  const data = (cache[id + lang.updated_at + getScript()] ||= await get(`/api/conlangs/${id}/dictionary.json${sq()}`));
  const ab = alphabetOrder(lang.profile.sounds);
  const entries = data.entries.map((e) => ({ ...e, k: ab.key(e.form), f: fold(e.form), e: fold(e.en) }));
  const byEnglish = entries;                                  // already sorted by English
  const byForm = [...entries].sort((a, b) => { for (let i = 0; i < Math.min(a.k.length, b.k.length); i++) if (a.k[i] !== b.k[i]) return a.k[i] - b.k[i]; return a.k.length - b.k.length; });
  const posOptions = [...new Set(entries.map((e) => e.pos.split("/")[0]))].sort();
  let dir = "en", q = "", pos = "";
  const search = h("input", { type: "search", placeholder: "Search words or meanings", "aria-label": "Search the dictionary", oninput: () => { q = fold(search.value.trim()); draw(); } });
  const dirSel = h("select", { "aria-label": "Direction", onchange: () => { dir = dirSel.value; draw(); } },
    h("option", { value: "en" }, `English → ${lang.name}`), h("option", { value: "con" }, `${lang.name} → English`));
  const posSel = h("select", { "aria-label": "Part of speech", onchange: () => { pos = posSel.value; draw(); } }, h("option", { value: "" }, "All types"), posOptions.map((p) => h("option", { value: p }, p)));
  const jump = h("div", { class: "jump", "aria-label": "Jump to letter" }), out = h("ul", { class: "entries" }), count = h("p", { class: "muted small" });
  function details(e) {
    const bits = [];
    if (e.gender) bits.push(e.gender);
    if (e.dual) bits.push("dual " + e.dual); if (e.plural) bits.push("plural " + e.plural);
    for (const [t, f] of Object.entries(e.tenses || {})) bits.push(t + " " + f);
    const ag = Object.entries(e.agreement || {}); if (ag.length && new Set(ag.map(([, v]) => v)).size > 1) bits.push("agrees: " + ag.slice(0, 3).map(([k, v]) => `${k} ${v}`).join(" / ") + (ag.length > 3 ? ` (+${ag.length - 3} more)` : ""));
    if (e.built) bits.push("built from " + e.built);
    if (e.related.length) bits.push("related: " + e.related.slice(0, 3).map((r) => `${r.form} (${r.en})`).join(", "));
    return bits.join(" · ");
  }
  function draw() {
    const src = dir === "en" ? byEnglish : byForm;
    const hits = src.filter((e) => (!pos || e.pos.startsWith(pos)) && (!q || e.f.includes(q) || e.e.includes(q)));
    const items = [], heads = [];
    let cur = null;
    hits.forEach((e) => {
      const head = q ? null : dir === "en" ? (fold(e.en)[0] || "#").toUpperCase() : ab.tokens(e.form)[0];
      if (head && head !== cur) { cur = head; heads.push(head); items.push(h("li", { id: "L-" + head }, h("span", { class: "letterhead " + (dir === "con" ? "word" : "") }, dir === "con" ? head.charAt(0).toUpperCase() + head.slice(1) + " " + head : head))); }
      const left = dir === "en" ? [h("span", { class: "head" }, e.en), " ", h("span", { class: "pos" }, e.pos)] : [h("span", { class: "head word" }, e.form), " ", h("span", { class: "ipa" }, e.ipa)];
      const right = dir === "en" ? [h("span", { class: "head word" }, e.form), " ", h("span", { class: "ipa" }, e.ipa)] : [h("span", { class: "head" }, e.en), " ", h("span", { class: "pos" }, e.pos)];
      const more = details(e);
      items.push(h("li", null, h("div", null, left), h("div", null, right, more ? h("div", { class: "more" }, more) : null)));
    });
    mount(out, ...items);
    mount(jump, ...heads.map((l) => h("button", { class: "word", onclick: () => document.getElementById("L-" + l)?.scrollIntoView({ block: "start" }) }, l)));
    count.textContent = hits.length ? `${hits.length.toLocaleString()} ${hits.length === 1 ? "entry" : "entries"}` : "";
    if (!hits.length) mount(out, h("li", { style: "display:block" }, h("p", { class: "muted" }, "No entries match. Try fewer letters, or search by the English meaning.")));
  }
  draw();
  return h("div", null, h("div", { class: "dicttools" }, search, h("div", { class: "opts" }, dirSel, posSel)), jump, count, out);
}

// ------------------------------------------------------------------ grammar book
async function bookTab(id, lang) {
  const md = (cache["book" + id + lang.updated_at + getScript()] ||= await text(`/api/conlangs/${id}/grammar-book.md${sq()}`));
  const { html, toc } = renderMarkdown(md);
  const article = h("article", { class: "prose", html });
  article.querySelector("h1")?.remove();
  const nav = h("nav", { class: "toc", "aria-label": "Contents" }, toc.map((t) => h("a", { class: "l" + t.level, href: "#/lang/" + id + "/book", onclick: (e) => { e.preventDefault(); document.getElementById(t.id)?.scrollIntoView({ block: "start" }); } }, t.text)));
  return h("div", { class: "book" }, nav, article);
}

// ------------------------------------------------------------------ downloads
function filesTab(id, lang) {
  const safe = lang.name.normalize("NFKD").replace(/[^\x00-\x7F]/g, "").replace(/\W+/g, "_") || "language";
  const row = (title, desc, path, file) => h("tr", null, h("td", null, h("b", null, title), h("div", { class: "muted small" }, desc)),
    h("td", { class: "num" }, button("Download", async () => { try { await download(path, file); } catch (e) { toast(errorText(e), true); } }, "small")));
  return h("div", null, h("h2", null, "Downloads"),
    h("table", null, h("tbody", null,
      row("Dictionary (Markdown)", "Both directions, with grammar notes. Opens in any text editor.", `/api/conlangs/${id}/dictionary.md${sq()}`, safe + "_dictionary.md"),
      row("Dictionary (spreadsheet)", "One row per word, for Excel or Google Sheets.", `/api/conlangs/${id}/dictionary.csv${sq()}`, safe + "_dictionary.csv"),
      row("Grammar book (Markdown)", "The full beginner's course.", `/api/conlangs/${id}/grammar-book.md${sq()}`, safe + "_grammar_book.md"))),
    h("p", { class: "muted small", style: "margin-top:1rem" }, "PDF versions are planned."));
}
