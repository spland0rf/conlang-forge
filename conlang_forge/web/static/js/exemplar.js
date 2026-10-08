// "Shape it from a sample": paste text in the sound you want, review what the system would change, approve in one go.
import { api, post } from "./api.js";
import { state } from "./state.js";
import { button, errorText, h, modal, toast } from "./ui.js";

const WHY = { conflict: "Differs from a setting you fixed", drift: "Differs from the language now" };

export function exemplarPanel(id, lang, S, onStage) {
  const modelOn = !!(state.config && state.config.model_available);
  const input = h("textarea", { rows: 5, maxlength: 20000, placeholder: "Paste sample words or sentences, one per line. Add a meaning after a | if you like:\nkorash vael tume | the old road", "aria-label": "Sample text", value: (S.exemplars || []).join("\n") });
  const grammar = h("input", { type: "checkbox", checked: modelOn, disabled: !modelOn || null });
  const out = h("div", { "aria-live": "polite" });

  async function analyze() {
    const texts = input.value.split("\n").map((t) => t.trim()).filter(Boolean);
    if (!texts.length) { toast("Paste some sample text first.", true); return; }
    out.replaceChildren(h("p", { class: "muted" }, h("span", { class: "spinner" }), " Reading the sample…"));
    try {
      const res = await post(`/api/conlangs/${id}/exemplars/analyze`, { texts, use_model: grammar.checked && modelOn });
      out.replaceChildren();
      if (res.usage) window.dispatchEvent(new Event("cf:usage"));
      review(res, texts);
    } catch (e) { out.replaceChildren(h("p", { class: "err", role: "alert" }, errorText(e))); }
  }

  function review(res, texts) {
    const sm = res.summary;
    const head = h("div", null,
      h("p", { class: "muted" }, `Read ${sm.words} words (${sm.syllables} syllables). Commonest sounds: ${sm.consonants || "none"}; vowels ${sm.vowels || "none"}.`),
      res.notes.map((n) => h("p", { class: "small muted" }, n)));
    if (!res.proposals.length) {
      modal("Sample analysis", h("div", null, head, h("p", null, "Nothing to change: the language already matches this sample.")), (close) => [h("button", { class: "primary", onclick: close }, "Close")]);
      return;
    }
    const checks = res.proposals.map((p) => h("input", { type: "checkbox", checked: true, "aria-label": "Use " + p.label }));
    const rows = res.proposals.map((p, i) => h("label", { class: "prop " + p.kind },
      h("div", { class: "row" }, checks[i], h("b", null, p.label), h("span", { class: "conf" }, p.confidence + " confidence"),
        p.source === "model" ? h("span", { class: "conf" }, "from the grammar reader") : null),
      h("div", { class: "small muted" }, WHY[p.kind] + ". " + p.evidence.charAt(0).toUpperCase() + p.evidence.slice(1)),
      h("div", { class: "small" }, h("span", { class: "muted" }, p.current_show), "  →  ", h("b", null, p.proposed_show))));
    const all = h("button", { class: "ghost small", onclick: () => { const on = checks.some((c) => !c.checked); checks.forEach((c) => (c.checked = on)); } }, "Select all / none");
    const body = h("div", { class: "proplist" }, head, h("p", null, `${res.proposals.length} setting${res.proposals.length === 1 ? "" : "s"} would change to match your sample. Untick any you do not want.`), all, rows);
    modal("The sample suggests these changes", body, (close) => [
      h("button", { onclick: close }, "Cancel"),
      h("button", { class: "primary", onclick: async () => {
        const chosen = res.proposals.filter((_, i) => checks[i].checked);
        try { await api("PUT", `/api/conlangs/${id}/exemplars`, { texts }); } catch {}
        close();
        if (chosen.length) onStage(chosen);
      } }, "Use selected settings")]);
  }

  return h("section", { class: "exemplar" },
    h("h2", { style: "font-size:1.1rem" }, "Shape the sound from a sample"),
    h("p", { class: "small muted" }, "Paste words or sentences that sound the way you want. The system reads the sounds (and, with a model, the grammar), then shows which settings would change. You approve them all at once or one by one. Nothing changes until you apply."),
    input,
    h("div", { class: "row between", style: "margin-top:.5rem" },
      h("label", { class: "check small muted", title: modelOn ? "Uses a few model tokens" : "No model is connected on this server" }, grammar, " Also read the grammar (uses the model)"),
      button("Analyze sample", analyze, "primary")),
    out);
}
