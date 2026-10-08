import { get, post, session } from "./api.js";
import { authPage } from "./auth.js";
import { accountPage } from "./account.js";
import { adminPage } from "./admin.js";
import { langPage, languagesPage } from "./languages.js";
import { fmtTokens, h, meter, mount, toast, errorText } from "./ui.js";

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
    h("a", { class: "brand", href: "#/" }, h("span", { "aria-hidden": "true", html: '<svg viewBox="0 0 32 32" width="26" height="26"><rect width="32" height="32" rx="7" fill="#3A3FB0"/><path d="M9 22V10h10M9 16h8M22 22l-2-12" stroke="#F0B429" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>' }), "Conlang Forge"),
    h("nav", { class: "nav", "aria-label": "Main" },
      link("#/", "Languages", path === "" || path.startsWith("lang")),
      u.role === "admin" ? link("#/admin/users", "Admin", path.startsWith("admin")) : null),
    h("a", { class: "meter-chip", href: "#/account", title: "Model tokens used today" },
      h("span", null, tok.limit == null ? `${fmtTokens(tok.used)} tokens today` : `${fmtTokens(tok.used)} of ${fmtTokens(tok.limit)} tokens today`),
      meter(tok.used, tok.limit, "Tokens used today")),
    h("a", { class: "acct", href: "#/account", "aria-current": path === "account" ? "page" : null }, u.display_name),
    h("button", { class: "ghost small", onclick: signOut }, "Sign out")));
}

async function signOut() {
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
  if (session.get() && !state.me) await loadMe();
  if (!state.me) { mount(app, authPage(state.config, async () => { await loadMe(); location.hash = "#/"; render(); })); return; }
  const path = location.hash.replace(/^#\/?/, "");
  const parts = path.split("/");
  const main = h("main", { class: "wrap", id: "main" }, h("p", { class: "muted" }, h("span", { class: "spinner" }), " Loading…"));
  mount(app, nav(path), main);
  try {
    let page;
    if (parts[0] === "lang" && parts[1]) page = await langPage(parts[1], parts[2] || "overview");
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
