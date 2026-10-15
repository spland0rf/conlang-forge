// Writing a language in a writing system: its primary script by default, or any other script of the user's, in which
// case each sound the script lacks is written with its closest sound.
import { get, post, put } from "./api.js";
import { button, errorText, h, mount, toast } from "./ui.js";

function label(s, langId) {
  return s.name + (s.primary ? " (primary)" : "") + (s.conlang_id === langId ? "" : s.conlang_name ? ` · made for ${s.conlang_name}` : " · free-standing");
}

// A script chooser plus the written result for the text returned by getText(). onScript(id) is told which script is shown.
export function writtenBox(id, getText, { onScript, auto = false } = {}) {
  const out = h("div", { class: "wr-out", "aria-live": "polite" });
  const sel = h("select", { "aria-label": "Writing system", onchange: () => { onScript && onScript(sel.value); show(); } });
  let list = null;

  async function load() {
    if (list) return;
    list = await get(`/api/conlangs/${id}/scripts`);
    if (!list.primary_id) { await post(`/api/conlangs/${id}/scripts/primary`, {}); list = await get(`/api/conlangs/${id}/scripts`); }
    const ordered = [...list.scripts].sort((a, b) => (b.id === list.primary_id) - (a.id === list.primary_id));
    mount(sel, ordered.map((s) => h("option", { value: s.id }, label(s, id))));
    sel.value = list.primary_id;
    onScript && onScript(sel.value);
  }

  async function show() {
    const text = (getText() || "").trim();
    if (!text) { mount(out, h("p", { class: "muted small" }, "There is nothing to write yet.")); return; }
    mount(out, h("p", { class: "muted" }, h("span", { class: "spinner" }), " Drawing…"));
    try {
      await load();
      const r = await post(`/api/conlangs/${id}/render`, { text, script_id: sel.value });
      mount(out, result(r));
    } catch (e) { mount(out, h("p", { class: "error", role: "alert" }, errorText(e))); }
  }

  function result(r) {
    const c = r.coverage, rows = c.approximate;
    const lines = r.sentences.length ? r.sentences.map((s) => h("div", { class: "wr-line" }, h("div", { class: "scr-svg", html: s.svg }))) : [h("p", { class: "muted" }, "No letters to draw.")];
    const note = r.designed_for_this
      ? h("p", { class: "muted small" }, `Designed for ${r.language}: every one of its ${c.total} sounds has its own letter.`)
      : h("p", { class: "muted small" }, `Not designed for ${r.language}. ${c.exact} of its ${c.total} sounds have an exact letter; the other ${rows.length} use the closest sound this script has.`);
    const table = !r.designed_for_this && rows.length
      ? h("details", { class: "notes" }, h("summary", null, "How the missing sounds are written"),
        h("table", { class: "wr-map" }, h("tbody", null, rows.map((x) => h("tr", null,
          h("td", { class: "word" }, x.sound), h("td", null, "→"), h("td", { class: "word" }, x.written_as.length ? x.written_as.join(" + ") : "(left out)"),
          h("td", { class: "muted small" }, x.how)))))) : null;
    return h("div", null, lines, note, table);
  }

  const node = h("div", { class: "wr-box" }, h("div", { class: "row" }, h("label", { class: "small muted" }, "Writing system "), sel), out);
  return { node, show, select: (sid) => { sel.value = sid; } , load };
}

// The language's Writing tab.
export async function writingTab(id, lang) {
  const wrap = h("div", { class: "writing" }, h("p", { class: "muted" }, h("span", { class: "spinner" }), " Designing the writing system…"));
  let primary;
  try { primary = await post(`/api/conlangs/${id}/scripts/primary`, {}); }
  catch (e) { return h("p", { class: "error", role: "alert" }, errorText(e)); }

  const sampleText = (primary.sentences || []).map((s) => s.text).join(" ");
  const input = h("textarea", { rows: 3, maxlength: 4000, class: "word", "aria-label": "Text of the language to write", placeholder: "Type or paste text in this language" }, sampleText);
  const specimen = h("div", { class: "scr-svg" });
  const actions = h("div", { class: "row" });
  const box = writtenBox(id, () => input.value, { onScript: showScript });
  const info = { cur: primary };

  async function showScript(sid) {
    try {
      info.cur = sid === primary.script_record.id ? primary : await get(`/api/scripts/${sid}`);
      const rec = info.cur.script_record;
      mount(specimen, h("div", { html: info.cur.specimen }));
      mount(actions,
        h("a", { class: "btn", href: `#/scripts/${rec.id}` }, "Edit this writing system"),
        h("a", { class: "btn", href: `#/scripts/new?lang=${id}` }, "Design another for this language"),
        rec.conlang_id === id && !rec.primary ? button("Make it the primary script", async () => {
          await put(`/api/conlangs/${id}/primary-script`, { script_id: rec.id }); toast("Primary script changed."); location.reload();
        }, "primary") : null);
    } catch (e) { toast(errorText(e), true); }
  }

  await box.load();
  mount(wrap,
    h("h2", null, "Write in the language's script"),
    h("p", { class: "muted" }, "Each language has a primary writing system with a letter for every one of its sounds. You can also write it in any other writing system you have made; sounds that script lacks use the closest one it has."),
    input,
    h("div", { class: "row", style: "margin:.6rem 0" }, button("Write", () => box.show(), "primary"),
      button("Use sample sentences", () => { input.value = sampleText; return box.show(); })),
    box.node, actions,
    h("details", { class: "notes", style: "margin-top:1rem" }, h("summary", null, "Letters of this writing system"), specimen));
  await box.show();
  return wrap;
}
