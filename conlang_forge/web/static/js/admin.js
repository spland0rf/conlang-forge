import { get, patch, post, put } from "./api.js";
import { SERIES_COLORS, rankedBars, stackedColumns } from "./charts.js";
import { ago, button, confirmBox, drawer, errorText, field, fmtTokens, fmtUsd, h, meter, modal, mount, nf, toast, when } from "./ui.js";

const DAY = 86400000;
const PURPOSES = ["exemplar.analyze", "book.polish", "translate.reduce", "translate.smooth", "admin.test"];
const PURPOSE_LABEL = { "exemplar.analyze": "Analyse example text", "book.polish": "Polish grammar book", "translate.reduce": "Translate: simplify", "translate.smooth": "Translate: smooth", "admin.test": "Admin test" };
const LIMITS = [["tokens_per_day", "Tokens per day"], ["tokens_per_month", "Tokens per month"], ["requests_per_minute", "Requests per minute"], ["max_conlangs", "Languages"], ["max_output_tokens", "Max reply length (tokens)"]];

export async function adminPage(tab = "users", arg) {
  const tabs = [["users", "Users"], ["usage", "Model usage"], ["audit", "Activity log"], ["settings", "Settings"]];
  const body = h("div");
  const node = h("div", null, h("h1", null, "Admin"),
    h("nav", { class: "tabs", "aria-label": "Admin sections" }, tabs.map(([k, l]) => h("a", { href: "#/admin/" + k, "aria-current": k === tab ? "page" : null }, l))), body);
  body.append(await ({ users: usersTab, usage: usageTab, audit: auditTab, settings: settingsTab }[tab] || usersTab)(arg));
  return { title: "Admin", node };
}

// ------------------------------------------------------------------ users
async function usersTab() {
  let q = "", status = "";
  const holder = h("div");
  async function load() {
    const params = new URLSearchParams({ q, status, limit: "100" });
    const { total, users } = await get("/api/admin/users?" + params);
    mount(holder, h("p", { class: "muted small" }, `${total} ${total === 1 ? "user" : "users"}`),
      h("div", { class: "scroll" }, h("table", null,
        h("thead", null, h("tr", null, ["Name", "Email", "Plan", "Role", "Status", "Last sign-in"].map((c) => h("th", null, c)))),
        h("tbody", null, users.map((u) => h("tr", { class: "click", tabindex: 0, onclick: () => openUser(u.id, load), onkeydown: (e) => e.key === "Enter" && openUser(u.id, load) },
          h("td", null, u.display_name), h("td", null, u.email), h("td", null, u.plan),
          h("td", null, u.role === "admin" ? h("span", { class: "tag admin" }, "admin") : "user"),
          h("td", null, h("span", { class: "tag " + (u.status === "active" ? "on" : "off") }, u.status)), h("td", null, ago(u.last_login_at))))))));
  }
  const search = h("input", { type: "search", placeholder: "Search by name or email", "aria-label": "Search users", oninput: () => { q = search.value; clearTimeout(search._t); search._t = setTimeout(load, 250); } });
  const st = h("select", { "aria-label": "Status", style: "width:auto", onchange: () => { status = st.value; load(); } },
    h("option", { value: "" }, "All"), h("option", { value: "active" }, "Active"), h("option", { value: "disabled" }, "Disabled"));
  await load();
  return h("div", null, h("div", { class: "row", style: "margin-bottom:1rem" }, h("div", { style: "flex:1;min-width:200px" }, search), st), holder);
}

async function openUser(id, reload) {
  const [u, { plans }] = await Promise.all([get("/api/admin/users/" + id), get("/api/admin/plans")]);
  const box = h("div");
  const close = drawer(box);
  const refresh = async () => { close(); reload && reload(); openUser(id, reload); };
  const act = (label, fn, cls = "") => button(label, async () => { try { await fn(); await refresh(); } catch (e) { toast(errorText(e), true); } }, cls + " small");
  const planSel = h("select", { onchange: async () => { try { await patch("/api/admin/users/" + id, { plan: planSel.value }); toast("Plan changed"); await refresh(); } catch (e) { toast(errorText(e), true); } } },
    plans.map((p) => h("option", { value: p.name, selected: p.name === u.plan }, p.name)));
  const roleSel = h("select", { onchange: async () => { try { await patch("/api/admin/users/" + id, { role: roleSel.value }); toast("Role changed"); await refresh(); } catch (e) { toast(errorText(e), true); } } },
    ["user", "admin"].map((r) => h("option", { value: r, selected: r === u.role }, r)));
  const inputs = Object.fromEntries(LIMITS.map(([k]) => [k, h("input", { type: "text", inputmode: "numeric", placeholder: "Plan: " + (u.limits.plan[k] == null ? "no limit" : nf.format(u.limits.plan[k])),
    value: u.limits.overrides[k] == null ? "" : String(u.limits.overrides[k]) })]));
  const saveLimits = async () => {
    const limits = {};
    for (const [k] of LIMITS) { const v = inputs[k].value.trim().toLowerCase(); limits[k] = v === "" ? null : v === "unlimited" ? -1 : Number(v); if (limits[k] !== null && !Number.isInteger(limits[k])) throw new Error("Limits must be whole numbers, or the word unlimited."); }
    await patch("/api/admin/users/" + id, { limits });
  };
  const us = u.usage;
  mount(box,
    h("div", { class: "row between" }, h("h2", { style: "margin:0" }, u.display_name), h("button", { class: "ghost", onclick: close, "aria-label": "Close" }, "Close")),
    h("p", { class: "muted" }, u.email), h("div", null, h("span", { class: "tag " + (u.status === "active" ? "on" : "off") }, u.status), u.role === "admin" ? h("span", { class: "tag admin" }, "admin") : null,
      u.disabled_reason ? h("div", { class: "hint" }, "Reason: " + u.disabled_reason) : null),
    h("dl", { class: "facts", style: "margin:1rem 0" }, h("dt", null, "Joined"), h("dd", null, when(u.created_at)), h("dt", null, "Last sign-in"), h("dd", null, when(u.last_login_at)),
      h("dt", null, "Languages"), h("dd", null, String(u.conlangs.length))),
    h("h3", null, "Plan and role"), h("div", { class: "row" }, h("div", { style: "flex:1" }, field("Plan", planSel)), h("div", { style: "flex:1" }, field("Role", roleSel))),
    h("h3", null, "Usage now"),
    [["Today", us.day], ["This month", us.month]].map(([l, p]) => h("div", { class: "field" }, h("div", { class: "row between" }, h("span", null, l), h("span", { class: "small muted" }, p.limit == null ? fmtTokens(p.used) + " used" : `${fmtTokens(p.used)} of ${fmtTokens(p.limit)}`)), meter(p.used, p.limit, l))),
    h("h3", null, "Limits for this user"), h("p", { class: "hint" }, "Leave blank to use the plan. Type a number to override, or the word unlimited."),
    LIMITS.map(([k, l]) => field(l, inputs[k])), act("Save limits", async () => { await saveLimits(); toast("Limits saved"); }, "primary"),
    h("h3", { style: "margin-top:1.5rem" }, "Account actions"),
    h("div", { class: "row" },
      u.status === "active" ? act("Disable account", async () => {
        const reason = h("input", { type: "text", placeholder: "Reason (optional)" });
        await new Promise((res, rej) => modal("Disable " + u.display_name + "?", field("Reason", reason, "They are signed out at once and cannot sign in until you enable the account."), (cl) => [
          h("button", { onclick: () => { cl(); rej(new Error("cancelled")); } }, "Cancel"), h("button", { class: "danger", onclick: async () => { cl(); try { await patch("/api/admin/users/" + id, { status: "disabled", reason: reason.value }); res(); } catch (e) { rej(e); } } }, "Disable")]));
      }, "danger") : act("Enable account", () => patch("/api/admin/users/" + id, { status: "active" }), "primary"),
      act("Set new password", async () => {
        const pw = h("input", { type: "text", autocomplete: "off" });
        await new Promise((res, rej) => modal("Set a new password", field("New password", pw, "Share it with the user safely. They are signed out everywhere."), (cl) => [
          h("button", { onclick: () => { cl(); rej(new Error("cancelled")); } }, "Cancel"), h("button", { class: "primary", onclick: async () => { cl(); try { await patch("/api/admin/users/" + id, { new_password: pw.value }); toast("Password set"); res(); } catch (e) { rej(e); } } }, "Set password")]));
      })),
    u.conlangs.length ? [h("h3", { style: "margin-top:1.5rem" }, "Their languages"), h("ul", null, u.conlangs.map((c) => h("li", null, h("span", { class: "word", style: "font-size:1.15rem" }, c.name), h("span", { class: "muted small" }, ` seed ${c.seed}`))))] : null);
}

// ------------------------------------------------------------------ usage
async function usageTab() {
  let days = 14, group = "purpose";
  const holder = h("div");
  async function load() {
    const end = Date.now() + 1, start = Math.floor((end - days * DAY) / DAY) * DAY;
    const qs = (extra) => new URLSearchParams({ start, end, ...extra });
    const [series, totals, top, calls] = await Promise.all([get("/api/admin/usage/series?" + qs({ bucket: "day", group_by: "purpose" })),
      get("/api/admin/usage/totals?" + qs({})), get("/api/admin/usage/top-users?" + qs({ limit: 8 })), get("/api/admin/usage/calls?limit=25")]);
    const buckets = [];
    for (let t = start; t < end; t += DAY) buckets.push({ t, label: new Date(t).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" }), parts: {}, cost: 0 });
    const idx = Object.fromEntries(buckets.map((b) => [b.t, b]));
    series.rows.forEach((r) => { const b = idx[r.bucket_start]; if (b) { b.parts[r.grp] = (b.parts[r.grp] || 0) + r.quota_tokens; b.cost += r.cost_micro_usd; } });
    const used = PURPOSES.filter((p) => buckets.some((b) => b.parts[p]));
    const sers = (used.length ? used : PURPOSES.slice(0, 1)).map((p) => ({ key: p, label: PURPOSE_LABEL[p], color: SERIES_COLORS[PURPOSES.indexOf(p)] }));
    mount(holder,
      h("div", { class: "kpis" }, [["Model calls", nf.format(totals.calls)], ["Tokens", fmtTokens(totals.quota_tokens)], ["Estimated cost", fmtUsd(totals.cost_micro_usd)],
        ["Failed", nf.format(totals.errors)]].map(([l, v]) => h("div", { class: "kpi" }, h("b", null, v), h("span", null, l)))),
      stackedColumns({ title: "Tokens per day", note: "By what the call was for. Days are UTC.", buckets, series: sers }),
      stackedColumns({ title: "Estimated cost per day", note: "US dollars, from the price table in Settings.", buckets: buckets.map((b) => ({ label: b.label, parts: { cost: b.cost } })),
        series: [{ key: "cost", label: "Cost", color: "var(--s1)" }], format: (v) => fmtUsd(v) }),
      rankedBars({ title: "Heaviest users", note: "Tokens in this period.", rows: top.users.map((u) => ({ label: u.display_name || u.email || u.user_id.slice(0, 6), value: u.quota_tokens, tip: `${u.email}<br>${nf.format(u.calls)} calls · ${fmtUsd(u.cost_micro_usd)}` })), format: fmtTokens }),
      h("h3", null, "Latest calls"),
      h("div", { class: "scroll" }, h("table", null,
        h("thead", null, h("tr", null, ["When", "Purpose", "Model", "Status", "Tokens", "Cost", "Time"].map((c, i) => h("th", { class: i > 3 ? "num" : "" }, c)))),
        h("tbody", null, calls.calls.length ? calls.calls.map((c) => h("tr", null, h("td", null, ago(c.created_at)), h("td", null, PURPOSE_LABEL[c.purpose] || c.purpose), h("td", null, c.model || ""),
          h("td", null, h("span", { class: "tag " + (c.status === "ok" ? "on" : "off") }, c.status + (c.error_code && c.status !== "ok" ? ": " + c.error_code : ""))),
          h("td", { class: "num" }, nf.format(c.quota_tokens)), h("td", { class: "num" }, fmtUsd(c.cost_micro_usd)), h("td", { class: "num" }, c.latency_ms + " ms")))
          : h("tr", null, h("td", { colspan: 7, class: "muted" }, "No calls yet. Calls appear here as soon as someone translates or analyses text."))))));
  }
  const range = h("select", { "aria-label": "Period", style: "width:auto", onchange: () => { days = Number(range.value); load(); } },
    [[7, "Last 7 days"], [14, "Last 14 days"], [30, "Last 30 days"], [60, "Last 60 days"]].map(([v, l]) => h("option", { value: v, selected: v === days }, l)));
  await load();
  return h("div", null, h("div", { class: "row", style: "margin-bottom:1rem" }, range), holder);
}

// ------------------------------------------------------------------ audit
async function auditTab() {
  const { entries } = await get("/api/admin/audit?limit=200");
  return h("div", { class: "scroll" }, h("table", null, h("thead", null, h("tr", null, ["When", "Action", "Target", "Details"].map((c) => h("th", null, c)))),
    h("tbody", null, entries.map((e) => h("tr", null, h("td", null, when(e.created_at)), h("td", null, e.action), h("td", { class: "small muted" }, (e.target_type || "") + " " + (e.target_id || "").slice(0, 8)),
      h("td", { class: "small" }, Object.entries(e.detail).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(", ")))))));
}

// ------------------------------------------------------------------ settings
async function settingsTab() {
  const [s, { plans }] = await Promise.all([get("/api/admin/settings"), get("/api/admin/plans")]);
  const save = async (obj) => { try { await put("/api/admin/settings", obj); toast("Saved"); } catch (e) { toast(errorText(e), true); } };
  const toggle = (key, label, hint) => {
    const c = h("input", { type: "checkbox", checked: !!s[key], onchange: () => save({ [key]: c.checked }) });
    return h("div", { class: "field" }, h("label", { style: "display:flex;gap:.6rem;align-items:center;margin:0" }, c, label), hint ? h("div", { class: "hint" }, hint) : null);
  };
  const cap = h("input", { type: "text", inputmode: "numeric", value: s["llm.global_tokens_per_day"] ?? "", placeholder: "No cap" });
  const prices = h("textarea", { rows: 6, spellcheck: false }, JSON.stringify(s["llm.prices"] || {}, null, 2));
  const testIn = h("input", { type: "text", placeholder: "Say hello in one sentence" }), testOut = h("div");
  const planRows = plans.map((p) => {
    const ins = Object.fromEntries(LIMITS.map(([k]) => [k, h("input", { type: "text", inputmode: "numeric", value: p[k] ?? "", placeholder: "none", "aria-label": p.name + " " + k, style: "width:7.5rem" })]));
    return h("tr", null, h("td", null, h("b", null, p.name), h("div", { class: "muted small" }, p.description)), LIMITS.map(([k]) => h("td", null, ins[k])),
      h("td", null, button("Save", async () => {
        const v = {}; for (const [k] of LIMITS) { const t = ins[k].value.trim(); v[k] = t === "" ? null : Number(t); if (t !== "" && !Number.isInteger(v[k])) return toast("Use whole numbers, or leave blank for no limit.", true); }
        try { await put("/api/admin/plans/" + p.name, v); toast("Plan saved"); } catch (e) { toast(errorText(e), true); }
      }, "small")));
  });
  return h("div", { class: "stack" },
    h("section", null, h("h2", null, "Access and safety"),
      toggle("registration.open", "Anyone can create an account", "Turn off to close sign-ups. Existing users keep access."),
      toggle("llm.enabled", "Language model calls are on", "The emergency stop: turning this off blocks every model call, for everyone, at once."),
      toggle("llm.store_previews", "Keep a short preview of each model call in the log", "Off by default. Stores the first 500 characters of the prompt and reply, which may include user text.")),
    h("section", null, h("h2", null, "Spending cap"), field("Most tokens all users together may use per day (UTC)", cap, "Leave blank for no cap."),
      button("Save cap", async () => { const t = cap.value.trim(); if (t && !/^\d+$/.test(t)) return toast("Use a whole number.", true); await save({ "llm.global_tokens_per_day": t ? Number(t) : null }); })),
    h("section", null, h("h2", null, "Plans"), h("p", { class: "muted small" }, "Defaults for everyone on a plan. Blank means no limit. Individual users can be overridden from the Users tab."),
      h("div", { class: "scroll" }, h("table", null, h("thead", null, h("tr", null, h("th", null, "Plan"), LIMITS.map(([, l]) => h("th", null, l)), h("th", null, ""))), h("tbody", null, planRows)))),
    h("section", null, h("h2", null, "Model prices"), h("p", { class: "muted small" }, "US dollars per million tokens, by model name: {\"model-name\": {\"in\": 3, \"out\": 15, \"cache_write\": 3.75, \"cache_read\": 0.3}}. Built-in prices are estimates; enter the real ones here."),
      prices, h("div", { style: "margin-top:.5rem" }, button("Save prices", async () => { try { await save({ "llm.prices": JSON.parse(prices.value || "{}") }); } catch (e) { toast("That is not valid JSON.", true); } }))),
    h("section", null, h("h2", null, "Try the model"), h("p", { class: "muted small" }, "Sends one short message through the same metered path as everything else. It shows up in the usage log as Admin test."),
      h("div", { class: "row" }, h("div", { style: "flex:1;min-width:240px" }, testIn), button("Send", async () => {
        try { const r = await post("/api/admin/llm-test", { prompt: testIn.value || "Say hello in one sentence." }); mount(testOut, h("p", { class: "ok" }, r.text, h("br"), h("span", { class: "small" }, `${r.model} · ${r.input_tokens} in, ${r.output_tokens} out · ${fmtUsd(r.cost_micro_usd)}`))); }
        catch (e) { mount(testOut, h("p", { class: "err", role: "alert" }, errorText(e))); }
      }, "primary")), testOut));
}
