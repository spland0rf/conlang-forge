// Checkpoints of a language or a writing system. Nothing is kept automatically: the owner presses "Create checkpoint",
// the current state is stored read only as the next numbered version, and the item carries on as the editable working
// version. "New version from this one" makes a separate editable copy that starts identical to an old checkpoint.
import { del, get, post } from "./api.js";
import { button, confirmBox, errorText, h, mount, toast } from "./ui.js";

const kb = (n) => (n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(n < 10240 ? 1 : 0)} KB` : `${(n / 1048576).toFixed(1)} MB`);
const when = (ms) => new Date(ms).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

// kind: "lang" or "script". prepare() may save pending edits first and returns false to stop.
export function versionsPanel({ kind, id, prepare }) {
  const base = kind === "lang" ? `/api/conlangs/${id}` : `/api/scripts/${id}`;
  const noun = kind === "lang" ? "language" : "writing system";
  const box = h("div", { class: "ver" });
  const viewer = h("div", { class: "ver-view", "aria-live": "polite" });
  const note = h("input", { type: "text", maxlength: 80, placeholder: "Optional note, e.g. before the new vowels", "aria-label": "Checkpoint note" });
  let state = null, shown = null;

  async function load() {
    try { state = await get(`${base}/versions`); draw(); } catch (e) { mount(box, h("p", { class: "error", role: "alert" }, errorText(e))); }
  }

  async function create() {
    if (prepare && (await prepare()) === false) return;
    try {
      state = await post(`${base}/versions`, { label: note.value });
      note.value = ""; shown = null; draw();
      toast(`Checkpoint v${state.versions[0].n} kept. You are now editing v${state.working}.`);
    } catch (e) { toast(errorText(e), true); }
  }

  async function view(n) {
    if (shown === n) { shown = null; mount(viewer); return; }
    shown = n;
    mount(viewer, h("p", { class: "muted" }, h("span", { class: "spinner" }), " Opening…"));
    try { mount(viewer, detail(await get(`${base}/versions/${n}`))); }
    catch (e) { mount(viewer, h("p", { class: "error", role: "alert" }, errorText(e))); }
  }

  async function branch(v) {
    if (!(await confirmBox(`New version from v${v.n}?`, `This makes a separate, editable ${noun} that starts identical to v${v.n}. Your current working version is not changed.`, "Create it"))) return;
    try {
      const r = await post(`${base}/versions/${v.n}/branch`, {});
      if (r.exact === false) toast("Made, but the letter generator has changed since this checkpoint, so the new copy is redrawn slightly differently.", true);
      else toast("Created. You are now editing the new copy.");
      location.hash = kind === "lang" ? `#/lang/${r.item.id}/` : `#/scripts/${r.item.script_record.id}`;
    } catch (e) { toast(errorText(e), true); }
  }

  async function remove(v) {
    if (!(await confirmBox(`Delete checkpoint v${v.n}?`, "The checkpoint is removed for good. Your working version is not affected.", "Delete", true))) return;
    try { state = await del(`${base}/versions/${v.n}`); shown = null; mount(viewer); draw(); }
    catch (e) { toast(errorText(e), true); }
  }

  function changes(list) {
    if (!list || !list.length) return h("p", { class: "muted small" }, "The working version has no differences from this checkpoint.");
    return h("details", { class: "notes", open: true }, h("summary", null, `What the working version has changed since (${list.length})`),
      h("table", null, h("tbody", null, list.map((c) => h("tr", null, h("td", null, c.label), h("td", { class: "word muted" }, String(c.then)), h("td", null, "→"), h("td", { class: "word" }, String(c.now)))))));
  }

  function detail(d) {
    const top = h("p", { class: "small" }, h("strong", null, `v${d.n}`), d.label ? ` · ${d.label}` : "", ` · kept ${when(d.created_at)} · `, h("em", null, "read only"));
    if (d.kind === "conlang") {
      return h("div", { class: "scr-card" }, top,
        h("p", null, `${d.name} · seed ${d.seed} · ${d.words} words · ${d.consonants.length} consonants, ${d.vowels.length} vowels`,
          d.typology ? ` · ${d.typology}` : "", d.word_order ? ` · word order ${d.word_order}` : ""),
        h("p", { class: "word" }, [...d.consonants, ...d.vowels].join(" ")), changes(d.changes_since));
    }
    return h("div", { class: "scr-card" }, top, h("p", null, `${d.name} · seed ${d.seed}`),
      h("div", { class: "scr-svg", html: d.sample }),
      d.sentences && d.sentences.length ? h("div", null, d.sentences.map((s) => h("div", { class: "wr-line" }, h("div", { class: "muted small" }, s.english), h("div", { class: "scr-svg", html: s.svg })))) : null,
      h("details", { class: "notes" }, h("summary", null, "Letters at this checkpoint"), h("div", { class: "scr-svg", html: d.specimen })),
      changes(d.changes_since));
  }

  function draw() {
    const s = state;
    const list = s.versions.length ? h("ul", { class: "ver-list" }, s.versions.map((v) => h("li", null,
      h("div", null, h("strong", null, `v${v.n}`), v.label ? ` · ${v.label}` : "", h("span", { class: "muted small" }, ` · ${when(v.created_at)} · ${kb(v.stored_bytes)}`)),
      h("div", { class: "row" }, button(shown === v.n ? "Hide" : "View", () => view(v.n), "small ghost"),
        button("New version from this one", () => branch(v), "small"), button("Delete", () => remove(v), "small ghost"))))) :
      h("p", { class: "muted" }, "No checkpoints yet. Nothing is kept unless you press the button above.");
    mount(box,
      h("p", { class: "muted" }, `A checkpoint keeps this ${noun} exactly as it is now, read only, so you can look back or start a new version from it. Nothing is kept automatically. You carry on editing the working version.`),
      s.branched_from ? h("p", { class: "small" }, `Started as a new version from “${s.branched_from.name}” v${s.branched_from.n}.`) : null,
      h("p", null, h("strong", null, s.has_checkpoints ? `Working version: v${s.working}` : "Working version"), h("span", { class: "muted" }, s.has_checkpoints ? " (editable)" : " (no checkpoints yet)")),
      h("div", { class: "row" }, note, button("Create checkpoint", create, "primary")),
      list, viewer);
  }

  mount(box, h("p", { class: "muted" }, h("span", { class: "spinner" }), " Loading…"));
  load();
  return box;
}
