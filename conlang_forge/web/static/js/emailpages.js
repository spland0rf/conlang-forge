import { post, session } from "./api.js";
import { button, errorText, field, h, mount } from "./ui.js";

// Pages opened from links in emails. They work signed in or out.
const shell = (...kids) => h("main", { class: "auth", id: "main" }, h("section", { class: "formside" }, h("div", null, ...kids)));

export function verifyPage(token, done) {
  const box = h("div", null, h("p", { class: "muted" }, h("span", { class: "spinner" }), " Confirming your email…"));
  (async () => {
    try {
      const r = await post("/api/auth/verify", { token });
      mount(box, h("p", { class: "ok" }, `Thanks. ${r.email} is confirmed.`), h("p", null, h("a", { href: "#/", onclick: () => setTimeout(done, 0) }, session.get() ? "Continue to your languages" : "Sign in")));
    } catch (e) {
      mount(box, h("p", { class: "err", role: "alert" }, errorText(e)), h("p", null, h("a", { href: "#/" }, session.get() ? "Go to your languages, where you can ask for a new link" : "Sign in to ask for a new link")));
    }
  })();
  return shell(h("h2", null, "Confirm your email"), box);
}

export function resetPage(token) {
  const pw = h("input", { type: "password", autocomplete: "new-password", required: true });
  const msg = h("div");
  const go = button("Set new password", async () => {
    msg.replaceChildren();
    try {
      await post("/api/auth/reset", { token, new_password: pw.value });
      session.clear();
      mount(box, h("p", { class: "ok" }, "Your password is changed. Sign in with the new one."), h("p", null, h("a", { href: "#/" }, "Sign in")));
    } catch (e) { msg.replaceChildren(h("p", { class: "err", role: "alert" }, errorText(e)), h("p", { class: "small" }, h("a", { href: "#/" }, "Ask for a new link from the sign-in page"))); }
  }, "primary");
  const box = h("div", null, msg, h("form", { onsubmit: (e) => { e.preventDefault(); go.click(); } },
    field("New password", pw, "At least 10 characters, with upper and lower case letters and a digit."), h("div", { class: "row" }, go), h("input", { type: "submit", class: "hidden" })));
  return shell(h("h2", null, "Choose a new password"), box);
}
