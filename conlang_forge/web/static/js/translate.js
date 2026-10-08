import { post } from "./api.js";
import { getScript } from "./script.js";
import { state } from "./state.js";
import { button, errorText, fmtTokens, h, mount, toast } from "./ui.js";

const EXAMPLES = ["The old wizard walked into the tavern and ordered a drink.", "Where did the king hide the sword?",
  "We will not surrender the castle to the dragon.", "Please bring me bread and water."];
const FROM_EXAMPLE_HINT = "Paste or type text in this language. Sentences end with . or ?";

function tokens(u) { return u ? (u.input || 0) + (u.output || 0) + (u.cache_write || 0) + Math.round((u.cache_read || 0) / 10) : 0; }

function interlinear(items) {
  return h("div", { class: "interlinear" }, items.map((it) => h("div", { class: "il" + (it.known === false ? " unk" : "") },
    h("span", { class: "form word" }, it.text), h("span", { class: "gl" }, it.gloss + (it.alts ? " / " + it.alts.join(" / ") : "")))));
}
function notes(issues) {
  const shown = (issues || []).filter((i) => i.level !== "info" && i.code !== "tense_unmarked");
  const info = (issues || []).filter((i) => i.level === "info" || i.code === "tense_unmarked");
  if (!shown.length && !info.length) return null;
  return h("details", { class: "notes", open: shown.length > 0 }, h("summary", null, shown.length ? `${shown.length} thing${shown.length > 1 ? "s" : ""} to know` : "Notes"),
    h("ul", null, [...shown, ...info].map((i) => h("li", null, i.message))));
}

export function translateTab(id, lang) {
  const modelOn = !!(state.config && state.config.model_available);
  let direction = "to";
  const out = h("div", { class: "tr-out", "aria-live": "polite" });
  const input = h("textarea", { rows: 4, maxlength: 4000, "aria-label": "Text to translate" });
  const smooth = h("input", { type: "checkbox", checked: modelOn });
  const smoothRow = h("label", { class: "check small muted", title: "Uses a few model tokens" }, smooth, " Make the English read naturally");
  const restricted = h("input", { type: "checkbox", checked: !modelOn });
  const restrictedRow = h("label", { class: "check small muted" }, restricted, " My text is already simple English (no model, free)");
  const tabsEl = h("div", { class: "seg", role: "group", "aria-label": "Direction" });
  const hint = h("p", { class: "muted small" });

  function setDirection(d) {
    direction = d;
    mount(tabsEl, h("button", { class: d === "to" ? "on" : "", "aria-pressed": String(d === "to"), onclick: () => setDirection("to") }, "English to " + lang.name),
      h("button", { class: d === "from" ? "on" : "", "aria-pressed": String(d === "from"), onclick: () => setDirection("from") }, lang.name + " to English"));
    input.placeholder = d === "to" ? "Write anything in English. Long sentences and everyday words are fine; they are simplified for you." : FROM_EXAMPLE_HINT;
    input.classList.toggle("word", d === "from");
    smoothRow.hidden = d !== "from" || !modelOn;
    restrictedRow.hidden = d !== "to";
    hint.textContent = d === "to" ? (modelOn ? "Your text is simplified to the language's vocabulary first, then translated. You can see and edit the simplified version afterwards." :
      "No language model is connected on this server, so write simple English (short sentences, everyday words).") : "";
    mount(out);
  }

  async function run(text, mode) {
    mount(out, h("p", { class: "muted" }, h("span", { class: "spinner" }), direction === "to" && mode === "english" ? " Simplifying and translating…" : " Translating…"));
    try {
      const body = direction === "to" ? { direction: "to", text, mode, script: getScript() } : { direction: "from", text, smooth: smooth.checked && modelOn };
      const res = await post(`/api/conlangs/${id}/translate`, body);
      mount(out, direction === "to" ? showTo(res) : showFrom(res));
      if (res.usage) window.dispatchEvent(new Event("cf:usage"));
    } catch (e) {
      mount(out, h("p", { class: "error", role: "alert" }, errorText(e)));
    }
  }

  function showTo(res) {
    const edit = h("textarea", { rows: 3, "aria-label": "Simplified English" }, res.re_text);
    const lines = res.sentences.map((s) => h("div", { class: "tr-sentence" }, h("div", { class: "big word" }, s.text),
      interlinear(s.forms.map((f, i) => ({ text: f, gloss: s.glosses[i] })))));
    return h("div", null, h("h2", { class: "sr-only" }, "Translation"), lines,
      h("div", { class: "card tr-edit" }, h("h3", null, res.mode === "english" ? "What was translated" : "Your simple English"),
        h("p", { class: "muted small" }, res.mode === "english" ? "Your text, simplified to this language's vocabulary. Edit it and translate again; that costs no tokens." : "Edit and translate again."),
        edit, h("div", { class: "row between", style: "margin-top:.6rem" },
          h("span", { class: "muted small" }, res.usage ? `Used ${fmtTokens(tokens(res.usage))} tokens` : "No tokens used"),
          button("Translate this version", () => run(edit.value, "restricted"), "primary small"))),
      notes(res.issues));
  }

  function showFrom(res) {
    return h("div", null, h("h2", { class: "sr-only" }, "Translation"),
      res.natural ? res.natural.map((t) => h("p", { class: "big-en" }, t)) : res.literal.map((t) => h("p", { class: "big-en" }, t)),
      res.natural ? h("p", { class: "muted small" }, "Literal reading: " + res.literal.join(" ")) : h("p", { class: "muted small" }, "This is a word-by-word reading. Smoothing it into natural English is optional and uses a few tokens."),
      res.interlinear.map((s) => interlinear(s)),
      h("p", { class: "muted small" }, res.usage ? `Used ${fmtTokens(tokens(res.usage))} tokens` : "No tokens used"),
      notes(res.issues));
  }

  const go = button("Translate", async () => {
    if (!input.value.trim()) { toast("Enter some text first.", true); return; }
    await run(input.value, direction === "to" ? (restricted.checked || !modelOn ? "restricted" : "english") : "english");
  }, "primary");
  setDirection("to");
  const example = h("button", { class: "ghost small", onclick: () => { input.value = EXAMPLES[Math.floor(Math.random() * EXAMPLES.length)]; } }, "Try an example");
  return h("div", { class: "translate" }, tabsEl, hint, input,
    h("div", { class: "row between", style: "margin:.6rem 0 1.2rem" }, h("div", { class: "row" }, go, example), h("div", null, smoothRow, restrictedRow)), out);
}
