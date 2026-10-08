// The Settings tab: every setting of a language, fixed or left random, plus the odds that steer the random ones.
// Nothing here edits words. Applying settings rebuilds the vocabulary from the rules.
import { get, post } from "./api.js";
import { exemplarPanel } from "./exemplar.js";
import { button, errorText, h, modal, toast } from "./ui.js";

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const clone = (x) => JSON.parse(JSON.stringify(x ?? null));
const pct = (x) => Math.round(x * 1000) / 10;

export async function settingsTab(id, lang) {
  const S = await get(`/api/conlangs/${id}/settings`);
  const by = Object.fromEntries(S.settings.map((s) => [s.key, s]));
  const original = { tuning: clone(S.tuning || {}) };
  const draft = { set: {}, unpin: new Set(), tuning: clone(S.tuning || {}) };
  const open = new Set(["sounds"]);
  const root = h("div", { class: "settings" });
  const bar = h("div", { class: "savebar", role: "region", "aria-label": "Pending changes" });

  // ---- state helpers
  // a count (how many) and its list (which ones) are two ways to set the same thing; the last one chosen wins
  const LIST_OF = { "phonology.consonant_count": "phonology.consonants", "phonology.vowel_count": "phonology.vowels", "phonology.complex_count": "phonology.complex_consonants" };
  const FREES = { "phonology.consonants": ["phonology.consonant_weights"], "phonology.vowels": ["phonology.vowel_weights"], "phonology.complex_consonants": ["phonology.consonant_weights"] };
  const cur = (k) => {
    if (k in draft.set) return draft.set[k];
    if (LIST_OF[k] && LIST_OF[k] in draft.set) return draft.set[LIST_OF[k]].length;
    return by[k].value;
  };
  const order = Object.keys(S.consonants);
  const ofList = (of) => of.split("+").flatMap((x) => (x === "complex" ? cur("phonology.complex_consonants") : cur(x))).sort((a, b) => order.indexOf(a) - order.indexOf(b));
  const pinned = (k) => k in draft.set || (by[k].pinned && !draft.unpin.has(k));
  const touched = (k) => (k in draft.set && (!by[k].pinned || !same(draft.set[k], by[k].value))) || (by[k].pinned && draft.unpin.has(k));
  const tuningChanged = () => !same(draft.tuning, original.tuning);
  const changeCount = () => Object.keys(by).filter((k) => "editable" in by[k] && touched(k)).length + (tuningChanged() ? 1 : 0);
  const redraw = () => { const y = window.scrollY; draw(); window.scrollTo(0, y); };
  const setVal = (k, v) => {
    draft.set[k] = v; draft.unpin.delete(k);
    if (LIST_OF[k]) { const l = LIST_OF[k]; delete draft.set[l]; if (by[l].pinned) draft.unpin.add(l); (FREES[l] || []).forEach((w) => { delete draft.set[w]; if (by[w].pinned) draft.unpin.add(w); }); }
    const cnt = Object.keys(LIST_OF).find((c) => LIST_OF[c] === k);
    if (cnt) { delete draft.set[cnt]; if (by[cnt].pinned) draft.unpin.add(cnt); }
    redraw();
  };
  const lock = (k) => { if (pinned(k)) { delete draft.set[k]; draft.unpin.add(k); } else { draft.set[k] = clone(by[k].value); draft.unpin.delete(k); } redraw(); };
  const tune = (kind, key, v) => { (draft.tuning[kind] ||= {}); if (v == null) delete draft.tuning[kind][key]; else draft.tuning[kind][key] = v; if (!Object.keys(draft.tuning[kind]).length) delete draft.tuning[kind]; };

  // ---- small controls
  const slider = (min, max, step, value, onchange, fmt = (x) => x) => {
    const num = h("input", { type: "number", min, max, step, value, "aria-label": "value" });
    const rng = h("input", { type: "range", min, max, step, value, "aria-label": "slider" });
    rng.addEventListener("input", () => { num.value = rng.value; });
    num.addEventListener("input", () => { rng.value = num.value; });
    const fire = (e) => { const v = parseFloat(e.target.value); if (!Number.isNaN(v)) onchange(Math.min(max, Math.max(min, v))); };
    rng.addEventListener("change", fire); num.addEventListener("change", fire);
    return h("div", { class: "slider" }, rng, num);
  };
  const chips = (options, selected, onchange, { disabled = () => false, min = 0 } = {}) => {
    const groups = [...new Set(options.map((o) => o.group || ""))];
    return h("div", null, groups.map((g) => h("div", { class: "chipgroup" }, g ? h("span", { class: "gname" }, g) : null,
      options.filter((o) => (o.group || "") === g).map((o) => {
        const on = selected.includes(o.value);
        return h("label", { class: "chip word" + (on ? " on" : ""), title: o.hint || o.label },
          h("input", { type: "checkbox", checked: on, disabled: disabled(o) || null, onchange: (e) => {
            const next = e.target.checked ? [...selected, o.value] : selected.filter((x) => x !== o.value);
            if (next.length < min) { toast(`Keep at least ${min}.`, true); redraw(); return; }
            onchange(next);
          } }), o.label);
      }))));
  };
  const labelOf = (c) => (S.consonants[c] ? S.consonants[c].label : S.vowels[c] ? S.vowels[c].label : c);

  function candidates(position) {
    const cons = cur("phonology.consonants"), man = (c) => S.consonants[c].manner, R = S.cluster_rules[position];
    let out = [];
    if (position === "onset") {
      for (const a of cons) for (const b of cons) if (a !== b && R.first.includes(man(a)) && R.second.includes(man(b)) && !R.never_first.includes(a)) out.push([a, b]);
      if (cons.includes("s")) for (const b of cons) if (man(b) === "stop" && b !== "ʔ" && !out.some((p) => p[0] === "s" && p[1] === b)) out.push(["s", b]);
    } else {
      const codas = cur("phonology.coda_consonants").filter((c) => cons.includes(c) || cur("phonology.complex_consonants").includes(c));
      for (const a of codas) for (const b of cons) if (a !== b && man(b) === "stop" && b !== "ʔ" && (R.first.includes(man(a)) || R.first_extra.includes(a))) out.push([a, b]);
    }
    return out;
  }

  function control(s) {
    const k = s.key, v = cur(k);
    switch (s.kind) {
      case "enum": {
        const sel = h("select", { "aria-label": s.label }, s.options.map((o) => h("option", { value: JSON.stringify(o.value), selected: same(o.value, v) }, o.label)));
        sel.addEventListener("change", () => setVal(k, JSON.parse(sel.value)));
        return sel;
      }
      case "bool": {
        const sel = h("select", { "aria-label": s.label }, [[true, s.yes], [false, s.no]].map(([b, t]) => h("option", { value: String(b), selected: v === b }, t)));
        sel.addEventListener("change", () => setVal(k, sel.value === "true"));
        return sel;
      }
      case "number": {
        let min = s.min;
        if (s.dynamic_min) {
          const t = S.minimums[s.dynamic_min][String(cur(s.dynamic_min === "consonants" ? "phonology.vowel_count" : "phonology.consonant_count"))];
          if (t) min = Math.max(min, t);
        }
        return h("div", null, slider(min, s.max, s.step, Math.max(v, min), (x) => setVal(k, s.integer ? Math.round(x) : x)),
          s.dynamic_min ? h("div", { class: "hint" }, `Lowest allowed: ${min}, the least that still gives a unique, consistent vocabulary with your other settings.`) : null);
      }
      case "text": { const i = h("input", { type: "text", maxlength: s.maxlen, value: v, "aria-label": s.label }); i.addEventListener("change", () => i.value.trim() && setVal(k, i.value.trim())); return i; }
      case "multi": {
        let opts = s.options;
        if (s.of) opts = opts.filter((o) => ofList(s.of).includes(o.value));
        if (k === "morphology.cases") {
          const core = { "nominative-accusative": ["nominative", "accusative"], "ergative-absolutive": ["ergative", "absolutive"] }[cur("morphology.case_alignment")];
          const other = ["nominative", "accusative", "ergative", "absolutive"].filter((c) => !core.includes(c));
          opts = opts.filter((o) => !other.includes(o.value));
          const sel = [...new Set([...(v.length ? core : []), ...v])];
          return h("div", null, chips(opts, sel, (n) => setVal(k, n), { disabled: (o) => core.includes(o.value) && v.length > 0 }),
            h("p", { class: "hint" }, "Leave all extra cases off for a language with no cases."));
        }
        return chips(opts, v.filter((x) => opts.some((o) => o.value === x)), (n) => setVal(k, n), { min: s.min || 0 });
      }
      case "weights": {
        const items = s.of ? ofList(s.of).map((c) => ({ value: c, label: labelOf(c) })) : s.items;
        const base = v || {};
        const floor = s.of ? Math.min(...Object.values(base).filter((x) => x > 0), 0.05) : 0;
        const get1 = (it) => (it.value in base ? base[it.value] : floor);
        const rows = items.map((it) => {
          const inp = slider(0, 100, 1, Math.round(get1(it) * 100), () => {
            const out = {};
            rows.forEach((r) => { out[r.item.value] = parseFloat(r.num.value || 0) / 100; });
            setVal(k, out);
          });
          const num = inp.querySelector("input[type=number]");
          return { item: it, num, node: h("div", { class: "wrow" }, h("span", { class: "word wl" }, it.label), inp, h("span", { class: "muted small" }, "%")) };
        });
        return h("div", { class: "weights" }, rows.map((r) => r.node));
      }
      case "clusters": {
        const cand = candidates(s.position), sel = (v || []).filter((id2) => cand.some((p) => p.join("+") === id2));
        if (!cand.length) return h("p", { class: "muted small" }, "No pairs are possible with the current consonants.");
        const opts = cand.map((p) => ({ value: p.join("+"), label: p.map(labelOf).join(""), hint: p.map((c) => S.consonants[c].say).join(" + ") }));
        return chips(opts, sel, (n) => setVal(k, n));
      }
      case "odds": return oddsRows(s);
      case "tune": return tuneRow(s);
      case "rate": return rateRow(s);
      default: return h("span", null, String(v));
    }
  }

  function oddsRows(s) {
    const k = s.key, over = (draft.tuning.odds || {})[k] || {};
    const rows = s.odds.map((o) => ({ ...o, w: o.key in over ? over[o.key] : o.default }));
    const total = rows.reduce((a, r) => a + r.w, 0) || 1;
    const inputs = rows.map((r) => h("input", { type: "number", min: 0, max: 1000, step: "any", value: Math.round(r.w * 1000) / 1000, "aria-label": "weight for " + r.label }));
    const write = () => {
      const o = {}; inputs.forEach((i, n) => { o[rows[n].key] = Math.max(0, parseFloat(i.value) || 0); });
      tune("odds", k, rows.every((r, n) => Math.abs(o[r.key] - r.default) < 1e-9) ? null : o);
      redraw();
    };
    inputs.forEach((i) => i.addEventListener("change", write));
    return h("div", { class: "odds" }, rows.map((r, n) => h("div", { class: "orow" }, h("span", null, r.label), inputs[n], h("span", { class: "muted small pc" }, pct(r.w / total) + "%"))),
      k in (draft.tuning.odds || {}) ? button("Back to the usual odds", () => { tune("odds", k, null); redraw(); }, "small ghost") : null);
  }
  function tuneRow(s) {
    const name = s.key.slice(4), cur1 = (draft.tuning.gen || {})[name], v = cur1 ?? s.default;
    return h("div", null, slider(s.min, s.max, s.step, v, (x) => { tune("gen", name, Math.abs(x - s.default) < 1e-9 ? null : (s.integer ? Math.round(x) : x)); redraw(); }),
      h("div", { class: "hint" }, `Usual value: ${s.default}`, cur1 != null ? [" · ", button("Reset", () => { tune("gen", name, null); redraw(); }, "small ghost")] : null));
  }
  function rateRow(s) {
    const cur1 = (draft.tuning.rates || {})[s.key], v = cur1 ?? s.default;
    return h("div", null, slider(0, 100, 1, Math.round(v * 100), (x) => { tune("rates", s.key, Math.abs(x / 100 - s.default) < 1e-9 ? null : x / 100); redraw(); }),
      h("div", { class: "hint" }, `Chance, in percent. Usual: ${Math.round(s.default * 100)}%`));
  }

  function oddsDetails(s) {
    if (s.odds && s.kind === "enum" && !s.odds.every((o) => o.default === 0)) {
      const probe = { ...s, kind: "odds" };
      const over = (draft.tuning.odds || {})[s.key];
      return h("details", { class: "odds-box", open: !!over }, h("summary", null, "Odds when random" + (over ? " (changed)" : "")),
        h("p", { class: "hint" }, "Relative weights; they do not need to add up to anything. They only matter while this setting is on Random."), oddsRows(probe));
    }
    if (s.chance) {
      const v = (draft.tuning.rates || {})[s.key] ?? s.chance.default;
      return h("details", { class: "odds-box", open: (draft.tuning.rates || {})[s.key] != null },
        h("summary", null, `Chance of "yes" when random: ${Math.round(v * 100)}%` + ((draft.tuning.rates || {})[s.key] != null ? " (changed)" : "")),
        slider(0, 100, 1, Math.round(v * 100), (x) => { tune("rates", s.key, Math.abs(x / 100 - s.chance.default) < 1e-9 ? null : x / 100); redraw(); }));
    }
    return null;
  }

  function row(s) {
    const editable = "editable" in s, k = s.key, isPinned = editable && pinned(k);
    const lockBtn = editable && !["odds", "rate", "tune"].includes(s.kind) ?
      h("button", { class: "lock" + (isPinned ? " fixed" : ""), "aria-pressed": String(isPinned), title: isPinned ? "Fixed: the generator will keep this. Click to leave it random." : "Random: the generator chooses. Click to fix it at its current value.", onclick: () => lock(k) },
        isPinned ? "Fixed" : "Random") : null;
    return h("div", { class: "srow" + (touched(k) ? " edited" : "") },
      h("div", { class: "shead" }, h("label", { class: "slabel" }, s.label), lockBtn),
      h("div", { class: "hint" }, s.help),
      h("div", { class: "scontrol" }, control(s)),
      editable && !["odds", "rate", "tune"].includes(s.kind) ? oddsDetails(s) : null);
  }

  function draw() {
    root.replaceChildren(...[
      exemplarPanel(id, lang, S, (changes) => {
        for (const c of changes) { draft.set[c.key] = c.proposed; draft.unpin.delete(c.key); }
        open.add("sounds");
        redraw();
        toast(`${changes.length} setting${changes.length === 1 ? "" : "s"} staged. Review them below, then apply.`);
      }),
      h("p", { class: "muted" }, "Fix a setting to hold it still, or leave it on Random and the generator picks it from the odds. Applying rebuilds the vocabulary by the rules; it never edits a word by hand."),
      S.groups.map((g) => {
        const items = S.settings.filter((s) => s.group === g.id && !(s.kind === "odds" && false));
        const edited = items.filter((s) => "editable" in s && touched(s.key)).length;
        const d = h("details", { class: "sgroup", open: open.has(g.id) || edited > 0 }, h("summary", null, g.label, edited ? h("span", { class: "badge" }, `${edited} changed`) : null),
          h("p", { class: "hint" }, g.help), items.map(row));
        d.addEventListener("toggle", () => (d.open ? open.add(g.id) : open.delete(g.id)));
        return d;
      }), bar].flat().filter(Boolean));
    const n = changeCount();
    bar.classList.toggle("on", n > 0);
    bar.replaceChildren(h("span", null, n ? `${n} change${n === 1 ? "" : "s"} not applied yet` : "No changes"),
      h("span", { class: "row" }, button("Discard", async () => { draft.set = {}; draft.unpin = new Set(); draft.tuning = clone(original.tuning); redraw(); }, "ghost"),
        button("Review and apply", review, "primary")));
  }

  const payload = () => ({ set: draft.set, unpin: [...draft.unpin], tuning: tuningChanged() ? draft.tuning : undefined });

  async function review() {
    let pre;
    try { pre = await post(`/api/conlangs/${id}/settings/preview`, payload()); } catch (e) { toast(errorText(e), true); return; }
    let mode = "replace";
    const mine = new Set(Object.keys(draft.set).concat([...draft.unpin]));
    const list = pre.changes.length ? h("table", { class: "diff" }, h("tbody", null, pre.changes.map((c) =>
      h("tr", null, h("td", null, h("b", null, c.label), mine.has(c.key) ? null : h("span", { class: "muted small" }, " (follows from your changes)")),
        h("td", { class: "muted" }, c.before), h("td", null, "→ ", c.after))))) :
      h("p", { class: "muted" }, "None of the visible settings change. The words may still be redrawn if odds or tendencies changed.");
    const radios = h("div", { class: "stack" },
      ...[["replace", "Rebuild this language", "Every word is regenerated from the new settings. The old words are not kept."],
          ["copy", "Save as a new language", "Keeps this language as it is and creates another one with these settings."]].map(([val, t, d], i) =>
        h("label", { class: "check" }, h("input", { type: "radio", name: "mode", checked: i === 0, onchange: () => { mode = val; } }), h("span", null, h("b", null, t), h("div", { class: "muted small" }, d)))));
    modal("Review changes", h("div", null, list, h("hr"), radios), (close) => [
      h("button", { onclick: close }, "Back"),
      h("button", { class: "primary", onclick: async (e) => {
        e.target.disabled = true; e.target.textContent = "Building…";
        try {
          const res = await post(`/api/conlangs/${id}/settings/apply`, { ...payload(), mode });
          close(); toast(mode === "copy" ? "Saved as a new language" : "Language rebuilt");
          location.hash = `#/lang/${res.id}/settings`; window.dispatchEvent(new Event("hashchange"));
        } catch (err) { e.target.disabled = false; e.target.textContent = "Apply"; toast(errorText(err), true); }
      } }, "Apply")]);
  }

  draw();
  return root;
}
