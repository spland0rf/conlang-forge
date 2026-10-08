import { get, patch, post } from "./api.js";
import { state } from "./state.js";
import { loadMe } from "./app.js";
import { button, errorText, field, fmtTokens, h, meter, toast, when } from "./ui.js";

export async function accountPage() {
  await loadMe();
  const me = state.me, u = me.usage;
  const name = h("input", { type: "text", value: me.display_name, maxlength: 80 });
  const old = h("input", { type: "password", autocomplete: "current-password" });
  const nw = h("input", { type: "password", autocomplete: "new-password" });
  const msg = h("div");
  const row = (label, used, limit, note) => h("div", { class: "field" },
    h("div", { class: "row between" }, h("b", null, label), h("span", { class: "small muted" }, limit == null ? `${fmtTokens(used)} used, no limit` : `${fmtTokens(used)} of ${fmtTokens(limit)}`)),
    meter(used, limit, label), note ? h("div", { class: "hint" }, note) : null);
  const lim = u.limits;
  return { title: "Account", node: h("div", { class: "cols" },
    h("section", null, h("h1", null, "Account"),
      h("dl", { class: "facts" }, h("dt", null, "Email"), h("dd", null, me.email), h("dt", null, "Plan"), h("dd", null, me.plan),
        h("dt", null, "Signed in with"), h("dd", null, [me.password_set ? "password" : null, ...me.providers.map((p) => p[0].toUpperCase() + p.slice(1))].filter(Boolean).join(", ")),
        h("dt", null, "Languages"), h("dd", null, lim.max_conlangs == null ? `${me.conlang_count}` : `${me.conlang_count} of ${lim.max_conlangs}`)),
      h("div", { style: "margin-top:1.5rem" }, field("Display name", name),
        button("Save name", async () => { try { await patch("/api/me", { display_name: name.value }); await loadMe(); toast("Name saved"); } catch (e) { toast(errorText(e), true); } })),
      h("h2", { style: "margin-top:2rem" }, me.password_set ? "Change password" : "Set a password"),
      !me.password_set ? h("p", { class: "muted small" }, "You signed in with Google. A password lets you also sign in with your email.") : null, msg,
      me.password_set ? field("Current password", old) : null, field("New password", nw, "At least 10 characters, upper and lower case, and a digit."),
      button(me.password_set ? "Change password" : "Set password", async () => {
        msg.replaceChildren();
        try { await post("/api/me/password", { old_password: old.value, new_password: nw.value }); old.value = nw.value = ""; await loadMe(); msg.replaceChildren(h("p", { class: "ok" }, "Password saved.")); }
        catch (e) { msg.replaceChildren(h("p", { class: "err", role: "alert" }, errorText(e))); }
      }, "primary")),
    h("section", null, h("h2", null, "Model usage"),
      h("p", { class: "muted small" }, "Tokens are the unit the language model is metered in. Forging a language and downloading books is free; translating and analysing text uses tokens."),
      row("Today", u.day.used, u.day.limit, u.day.limit == null ? null : `Resets ${when(u.day.resets_at)}`),
      row("This month", u.month.used, u.month.limit, u.month.limit == null ? null : `Resets ${when(u.month.resets_at)}`),
      h("p", { class: "small muted" }, u.requests_this_minute.limit == null ? "No request rate limit." : `Up to ${u.requests_this_minute.limit} model requests per minute.`))) };
}
