import { get, post, session } from "./api.js";
import { button, errorText, field, h, mount } from "./ui.js";

function loadGoogle(clientId, onCredential, slot) {
  const init = () => {
    window.google.accounts.id.initialize({ client_id: clientId, callback: (r) => onCredential(r.credential), ux_mode: "popup" });
    window.google.accounts.id.renderButton(slot, { theme: "outline", size: "large", text: "continue_with", width: 320 });
  };
  if (window.google && window.google.accounts) return init();
  const s = h("script", { src: "https://accounts.google.com/gsi/client", async: true, defer: true, onload: init, onerror: () => { slot.textContent = "Google sign-in could not be loaded."; } });
  document.head.append(s);
}

export function authPage(config, onDone) {
  let mode = "in";
  const msg = h("div");
  const form = h("div");
  async function finish(sess) { session.set(sess); await onDone(); }

  // Shown after sign-up, and when someone tries to sign in before confirming their email.
  function checkEmail(address, justCreated) {
    const note = h("div");
    const again = button("Send the link again", async () => {
      try { await post("/api/auth/resend", { email: address }); note.replaceChildren(h("p", { class: "ok" }, "Sent. It can take a minute to arrive.")); }
      catch (e) { note.replaceChildren(h("p", { class: "err", role: "alert" }, errorText(e))); }
    });
    mount(form, h("h3", null, "Check your email"),
      h("p", null, justCreated ? "Your account is created. We sent a verification link to " : "This account is not confirmed yet. We sent a verification link to ", h("b", null, address), "."),
      h("p", null, "Open the email and click the link to confirm your address. ", h("b", null, "You won't be able to log in until you have verified your account.")),
      h("p", { class: "muted small" }, "The link works for 48 hours. If you don't see the email, look in your spam or junk folder."),
      note, h("div", { class: "row" }, button("Login", () => { mode = "in"; draw(); }, "primary"), again));
  }

  function draw() {
    const email = h("input", { type: "email", autocomplete: "email", required: true, placeholder: "you@example.com" });
    const name = h("input", { type: "text", autocomplete: "name", placeholder: "Optional" });
    const pw = h("input", { type: "password", autocomplete: mode === "in" ? "current-password" : "new-password", required: true });
    const submit = button(mode === "in" ? "Sign in" : "Create account", async () => {
      msg.replaceChildren();
      try {
        const sess = mode === "in" ? await post("/api/auth/login", { email: email.value, password: pw.value })
          : await post("/api/auth/register", { email: email.value, password: pw.value, display_name: name.value });
        if (sess.verification_required) return checkEmail(sess.email, true);
        await finish(sess);
      } catch (e) {
        if (e.code === "email_not_verified") return checkEmail((e.detail && e.detail.email) || email.value, false);
        msg.replaceChildren(h("p", { class: "err", role: "alert" }, errorText(e)));
      }
    }, "primary");
    const gslot = h("div");
    if (mode === "forgot") {
      const fe = h("input", { type: "email", autocomplete: "email", required: true, value: email.value, placeholder: "you@example.com" });
      const send = button("Send reset link", async () => {
        msg.replaceChildren();
        try { const r = await post("/api/auth/forgot", { email: fe.value }); msg.replaceChildren(h("p", { class: "ok" }, r.message)); }
        catch (e) { msg.replaceChildren(h("p", { class: "err", role: "alert" }, errorText(e))); }
      }, "primary");
      mount(form, h("h3", null, "Forgot your password?"), h("p", { class: "muted small" }, "Enter your email address and we will send you a link to choose a new one."), msg,
        h("form", { onsubmit: (e) => { e.preventDefault(); send.click(); } }, field("Email", fe), h("div", { class: "row" }, send), h("input", { type: "submit", class: "hidden" })),
        h("p", null, h("a", { href: "#/", onclick: (e) => { e.preventDefault(); mode = "in"; msg.replaceChildren(); draw(); } }, "Back to sign in")));
      return;
    }
    mount(form,
      h("div", { class: "seg", role: "group", "aria-label": "Sign in or create an account" },
        h("button", { "aria-pressed": mode === "in", onclick: () => { mode = "in"; draw(); } }, "Sign in"),
        config.registration_open ? h("button", { "aria-pressed": mode === "up", onclick: () => { mode = "up"; draw(); } }, "Create account") : null),
      msg,
      h("form", { onsubmit: (e) => { e.preventDefault(); submit.click(); } },
        field("Email", email), mode === "up" ? field("Name", name) : null,
        field("Password", pw, mode === "up" ? "At least 10 characters, with upper and lower case letters and a digit." : null),
        h("div", { class: "row" }, submit), h("input", { type: "submit", class: "hidden" })),
      mode === "in" ? h("p", { class: "small" }, h("a", { href: "#/", onclick: (e) => { e.preventDefault(); mode = "forgot"; msg.replaceChildren(); draw(); } }, "Forgot your password?")) : null,
      config.google_client_id ? [h("div", { class: "divider" }, "or"), gslot] : null);
    if (config.google_client_id) loadGoogle(config.google_client_id, async (cred) => {
      try { await finish(await post("/api/auth/google", { credential: cred })); }
      catch (e) { msg.replaceChildren(h("p", { class: "err", role: "alert" }, errorText(e))); }
    }, gslot);
  }
  draw();
  return h("main", { class: "auth", id: "main" },
    h("section", { class: "pitch" },
      h("h1", null, "Give your world a language of its own."),
      h("p", null, "Forge a complete invented language in seconds: sounds, grammar, a 2,000-word dictionary and a beginner's course. Then keep it, read it, and share it with your players."),
      h("div", { class: "sample", lang: "x-zuro" }, "Kudchizve baz.", h("small", null, "“Hello, friend.” From Zuroeh, a language forged from seed 5."))),
    h("section", { class: "formside" }, h("div", null, h("h2", null, "Welcome"), form)));
}
