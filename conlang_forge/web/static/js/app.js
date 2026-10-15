import { get, post, session } from "./api.js";
import { authPage } from "./auth.js";
import { accountPage } from "./account.js";
import { resetPage, verifyPage } from "./emailpages.js";
import { adminPage } from "./admin.js";
import { scriptsPage } from "./scripts.js";
import { langPage, languagesPage } from "./languages.js";
import { button, fmtTokens, h, meter, mount, toast, errorText } from "./ui.js";

import { state } from "./state.js";
export { state };
const app = document.getElementById("app");

export async function loadMe() {
  try { state.me = await get("/api/me"); } catch { state.me = null; }
  return state.me;
}

function nav(path) {
  const link = (href, label, match) => h("a", { href, "aria-current": match ? "page" : null }, label);
  const u = state.me, tok = u.usage.day;
  return h("header", { class: "top" }, h("div", { class: "in" },
    h("a", { class: "brand", href: "#/" }, h("span", { "aria-hidden": "true", html: '<img src="/static/favicon.svg" width="26" height="26" alt="">' }), "Conlang Forge"),
    h("nav", { class: "nav", "aria-label": "Main" },
      link("#/", "Languages", path === "" || path.startsWith("lang")),
      link("#/scripts", "Writing systems", path.startsWith("scripts")),
      u.role === "admin" ? link("#/admin/users", "Admin", path.startsWith("admin")) : null),
    h("a", { class: "meter-chip", href: "#/account", title: "Model tokens used today" },
      h("span", null, tok.limit == null ? `${fmtTokens(tok.used)} tokens today` : `${fmtTokens(tok.used)} of ${fmtTokens(tok.limit)} tokens today`),
      meter(tok.used, tok.limit, "Tokens used today")),
    h("a", { class: "acct", href: "#/account", "aria-current": path === "account" ? "page" : null }, u.display_name),
    h("button", { class: "ghost small", onclick: signOut }, "Sign out")));
}

function unverifiedBanner() {
  const u = state.me;
  if (u.email_verified) return null;
  const note = h("span", null, state.config.verified_email_required
    ? "Confirm your email address to translate and analyse text. We sent a link to " + u.email + "."
    : "Please confirm your email address. We sent a link to " + u.email + ".");
  const b = button("Send it again", async () => {
    try { await post("/api/me/verify/resend"); toast("Sent. Check your inbox and spam folder."); } catch (e) { toast(errorText(e), true); }
  }, "small");
  return h("div", { class: "banner", role: "status" }, note, " ", b);
}

export async function signOut() {
  const s = session.get();
  try { s && await post("/api/auth/logout", { refresh_token: s.refresh_token }); } catch {}
  session.clear(); state.me = null; render();
}

let token = 0;
export async function render() {
  const my = ++token;
  if (!state.config) {
    try { state.config = await get("/api/config"); } catch { mount(app, h("p", { class: "wrap" }, "The server is not reachable.")); return; }
  }
  const hp = location.hash.replace(/^#\/?/, "").split("/");
  if ((hp[0] === "verify" || hp[0] === "reset") && hp[1]) {           // links from emails work signed in or out
    mount(app, hp[0] === "verify" ? verifyPage(hp[1], () => { state.me = null; render(); }) : resetPage(hp[1]));
    return;
  }
  if (session.get() && !state.me) await loadMe();
  if (!state.me) { mount(app, authPage(state.config, async () => { await loadMe(); location.hash = "#/"; render(); })); return; }
  const path = location.hash.replace(/^#\/?/, "");
  const parts = path.split("/");
  const main = h("main", { class: "wrap", id: "main" }, h("p", { class: "muted" }, h("span", { class: "spinner" }), " Loading…"));
  mount(app, nav(path), unverifiedBanner(), main);
  try {
    let page;
    if (parts[0] === "lang" && parts[1]) page = await langPage(parts[1], parts[2] || "overview");
    else if (parts[0] === "scripts") page = await scriptsPage(parts[1]);
    else if (parts[0] === "account") page = await accountPage();
    else if (parts[0] === "admin" && state.me.role === "admin") page = await adminPage(parts[1] || "users", parts[2]);
    else page = await languagesPage();
    if (my !== token) return;
    if (page.wide) main.classList.add("wide");
    mount(main, page.node || page);
    window.scrollTo(0, 0);
    document.title = (page.title ? page.title + " – " : "") + "Conlang Forge";
  } catch (e) {
    if (my !== token) return;
    mount(main, h("p", { class: "err", role: "alert" }, errorText(e)), h("a", { href: "#/" }, "Back to your languages"));
  }
}
window.addEventListener("hashchange", render);
window.addEventListener("cf:usage", async () => {
  try { await loadMe(); } catch {}
  const old = document.querySelector("header.top");
  if (old && state.me) old.replaceWith(nav(location.hash.replace(/^#\/?/, "")));
});
window.addEventListener("cf:signedout", () => { state.me = null; render(); });
render();
