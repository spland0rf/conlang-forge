// The administrator's area: users, model usage, the activity log and settings. Mirrors the website's admin pages; the
// server decides who may use them, this screen is only shown to administrators.
import React, { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, FlatList, Modal, Pressable, ScrollView, Text, View } from "react-native";
import { LIMITS, PURPOSE_LABEL, PURPOSES, auditDetail, limitText, makeBuckets, parseCap, parsePlanLimits, parsePrices, parseUserLimits, purposeColor, usageRange, usedPurposes, type SeriesRow } from "../adminModel";
import { ago, errorText, fmtLimitTokens, fmtTokens, fmtUsd, nf, when } from "../format";
import { useSession } from "../session";
import { Button, Card, Check, ErrorText, Field, H1, H2, Meter, Muted, OkText, Segmented, Select, Tag, TextPrompt } from "../ui/components";
import { RankedBars, StackedColumns } from "../ui/charts";
import { colors } from "../ui/theme";

type Tab = "users" | "usage" | "audit" | "settings";
const TABS: [Tab, string][] = [["users", "Users"], ["usage", "Usage"], ["audit", "Log"], ["settings", "Settings"]];

export default function AdminScreen() {
  const [tab, setTab] = useState<Tab>("users");
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg, paddingTop: 16 }}>
      <View style={{ paddingHorizontal: 20 }}>
        <H1>Admin</H1>
        <Segmented value={tab} onChange={(v) => setTab(v as Tab)} options={TABS.map(([k, l]) => [k, l] as [string, string])} />
      </View>
      <View style={{ flex: 1 }}>
        {tab === "users" ? <UsersTab /> : tab === "usage" ? <UsageTab /> : tab === "audit" ? <AuditTab /> : <SettingsTab />}
      </View>
    </View>
  );
}

// ------------------------------------------------------------------ users
function UsersTab() {
  const { api } = useSession();
  const [q, setQ] = useState(""), [status, setStatus] = useState("");
  const [data, setData] = useState<{ total: number; users: any[] } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const timer = useRef<any>(null);

  const load = useCallback(async (query = q, st = status) => {
    setErr(null);
    try { setData(await api.get(`/api/admin/users?${new URLSearchParams({ q: query, status: st, limit: "100" })}`)); } catch (e) { setErr(errorText(e)); }
  }, [api, q, status]);
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  return (
    <View style={{ flex: 1 }}>
      <View style={{ paddingHorizontal: 20 }}>
        <Field label="Search by name or email" value={q} autoCapitalize="none" autoCorrect={false}
          onChangeText={(v: string) => { setQ(v); clearTimeout(timer.current); timer.current = setTimeout(() => load(v, status), 300); }} />
        <Segmented value={status} onChange={(v) => { setStatus(v); load(q, v); }} options={[["", "All"], ["active", "Active"], ["disabled", "Disabled"]]} />
        <ErrorText>{err}</ErrorText>
        <Muted>{data ? `${data.total} ${data.total === 1 ? "user" : "users"}` : ""}</Muted>
      </View>
      <FlatList data={data?.users ?? []} keyExtractor={(u: any) => u.id} contentContainerStyle={{ padding: 20, paddingTop: 8 }}
        ListEmptyComponent={data ? <Muted>No users match.</Muted> : <ActivityIndicator color={colors.accent} />}
        renderItem={({ item: u }: any) => (
          <Pressable accessibilityRole="button" accessibilityLabel={"Open " + u.display_name} onPress={() => setOpen(u.id)}>
            <Card>
              <Text style={{ fontSize: 17, fontWeight: "700", color: colors.ink }}>{u.display_name}</Text>
              <Muted>{u.email}</Muted>
              <View style={{ flexDirection: "row", marginTop: 6, flexWrap: "wrap", gap: 4, alignItems: "center" }}>
                <Tag>{u.plan}</Tag>
                {u.role === "admin" ? <Tag tone="admin">admin</Tag> : null}
                {u.debug_mode && u.role !== "admin" ? <Tag tone="debug">debug</Tag> : null}
                <Tag tone={u.status === "active" ? "on" : "off"}>{u.status}</Tag>
                <Muted>{"signed in " + ago(u.last_login_at)}</Muted>
              </View>
            </Card>
          </Pressable>
        )} />
      <Modal visible={!!open} animationType="slide" onRequestClose={() => setOpen(null)}>
        {open ? <UserDetail id={open} onClose={() => setOpen(null)} onChanged={() => load()} /> : null}
      </Modal>
    </View>
  );
}

function UserDetail({ id, onClose, onChanged }: { id: string; onClose: () => void; onChanged: () => void }) {
  const { api, me } = useSession();
  const [u, setU] = useState<any>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [limits, setLimits] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<null | "disable" | "password">(null);

  const load = useCallback(async () => {
    try {
      const [user, p] = await Promise.all([api.get<any>(`/api/admin/users/${id}`), api.get<{ plans: any[] }>("/api/admin/plans")]);
      setU(user); setPlans(p.plans);
      setLimits(Object.fromEntries(LIMITS.map(([k]) => [k, limitText(user.limits.overrides[k])])));
    } catch (e) { setErr(errorText(e)); }
  }, [api, id]);
  useEffect(() => { load(); }, [load]);

  const patch = async (body: Record<string, unknown>, done: string) => {
    setErr(null); setOk(null);
    try { await api.patch(`/api/admin/users/${id}`, body); setOk(done); onChanged(); await load(); } catch (e) { setErr(errorText(e)); }
  };

  if (!u) return <View style={{ flex: 1, backgroundColor: colors.bg, justifyContent: "center", padding: 20 }}>{err ? <><ErrorText>{err}</ErrorText><Button title="Close" kind="ghost" onPress={onClose} /></> : <ActivityIndicator color={colors.accent} />}</View>;
  const isSelf = me?.id === id;
  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.bg }} contentContainerStyle={{ padding: 20, paddingTop: 56, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
      <Text accessibilityRole="button" onPress={onClose} style={{ color: colors.accent, fontSize: 16, marginBottom: 6 }}>‹ Users</Text>
      <H1>{u.display_name}</H1>
      <Muted>{u.email}</Muted>
      <View style={{ flexDirection: "row", marginVertical: 8 }}><Tag tone={u.status === "active" ? "on" : "off"}>{u.status}</Tag>{u.role === "admin" ? <Tag tone="admin">admin</Tag> : null}</View>
      {u.disabled_reason ? <Muted>{"Reason: " + u.disabled_reason}</Muted> : null}
      <Muted>{`Joined ${when(u.created_at)} · last sign-in ${when(u.last_login_at)} · ${u.conlangs.length} languages`}</Muted>
      <ErrorText>{err}</ErrorText><OkText>{ok}</OkText>

      <H2>Plan and role</H2>
      <Muted style={{ marginBottom: 4 }}>Plan</Muted>
      <Select label="Plan" value={u.plan} onChange={(v: string) => patch({ plan: v }, "Plan changed")} options={plans.map((p) => ({ value: p.name, label: p.name }))} />
      <Muted style={{ marginTop: 10, marginBottom: 4 }}>Role</Muted>
      <Select label="Role" value={u.role} onChange={(v: string) => patch({ role: v }, "Role changed")} options={["user", "admin"].map((r) => ({ value: r, label: r }))} />
      {u.role === "admin" ? <Muted style={{ marginTop: 8 }}>Debug mode is always on for administrators.</Muted>
        : <Check label="Debug mode: shows developer tools such as the settings export" value={!!u.debug} onChange={(v) => patch({ debug_mode: v }, v ? "Debug mode on" : "Debug mode off")} />}

      <H2>Usage now</H2>
      {([["Today", u.usage.day], ["This month", u.usage.month]] as [string, any][]).map(([l, p]) => (
        <View key={l} style={{ marginBottom: 10 }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}><Text style={{ color: colors.ink }}>{l}</Text><Muted>{p.limit == null ? fmtTokens(p.used) + " used" : `${fmtTokens(p.used)} of ${fmtTokens(p.limit)}`}</Muted></View>
          <Meter used={p.used} limit={p.limit} label={l} />
        </View>
      ))}

      <H2>Limits for this user</H2>
      <Muted style={{ marginBottom: 8 }}>Leave blank to use the plan. Type a number to override, or the word unlimited.</Muted>
      {LIMITS.map(([k, l]) => (
        <Field key={k} label={l} value={limits[k] ?? ""} onChangeText={(v: string) => setLimits({ ...limits, [k]: v })} autoCapitalize="none"
          placeholder={"Plan: " + (u.limits.plan[k] == null ? "no limit" : nf(u.limits.plan[k]))} />
      ))}
      <Button title="Save limits" onPress={async () => { try { await patch({ limits: parseUserLimits(limits) }, "Limits saved"); } catch (e) { setErr(errorText(e)); } }} />

      <H2>Account actions</H2>
      <View style={{ gap: 10 }}>
        {u.status === "active"
          ? <Button title="Disable account" kind="ghost" disabled={isSelf} onPress={() => setPrompt("disable")} />
          : <Button title="Enable account" onPress={() => patch({ status: "active" }, "Account enabled")} />}
        {isSelf ? <Muted>You cannot disable your own account here.</Muted> : null}
        <Button title="Set new password" kind="ghost" onPress={() => setPrompt("password")} />
      </View>

      {u.conlangs.length ? (<>
        <H2>Their languages</H2>
        {u.conlangs.map((c: any) => <Muted key={c.id}>{`${c.name} · seed ${c.seed}`}</Muted>)}
      </>) : null}

      <TextPrompt visible={prompt === "disable"} title={`Disable ${u.display_name}?`} message="They are signed out at once and cannot sign in until you enable the account." label="Reason (optional)" confirm="Disable" danger
        onCancel={() => setPrompt(null)} onOk={(reason) => { setPrompt(null); patch({ status: "disabled", reason }, "Account disabled"); }} />
      <TextPrompt visible={prompt === "password"} title="Set a new password" message="Share it with the user safely. They are signed out everywhere." label="New password" confirm="Set password" secure
        onCancel={() => setPrompt(null)} onOk={(pw) => { setPrompt(null); patch({ new_password: pw }, "Password set"); }} />
    </ScrollView>
  );
}

// ------------------------------------------------------------------ usage
function UsageTab() {
  const { api } = useSession();
  const [days, setDays] = useState(14);
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null); setD(null);
    const { start, end } = usageRange(days);
    const qs = (extra: Record<string, string | number>) => new URLSearchParams({ start: String(start), end: String(end), ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, String(v)])) });
    try {
      const [series, totals, top, calls] = await Promise.all([api.get<any>("/api/admin/usage/series?" + qs({ bucket: "day", group_by: "purpose" })),
        api.get<any>("/api/admin/usage/totals?" + qs({})), api.get<any>("/api/admin/usage/top-users?" + qs({ limit: 8 })), api.get<any>("/api/admin/usage/calls?limit=25")]);
      setD({ buckets: makeBuckets(series.rows as SeriesRow[], start, end), totals, top: top.users, calls: calls.calls });
    } catch (e) { setErr(errorText(e)); }
  }, [api, days]);
  useEffect(() => { load(); }, [load]);

  const used = d ? usedPurposes(d.buckets) : [];
  const shown = (used.length ? used : PURPOSES.slice(0, 1));
  return (
    <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 4, paddingBottom: 60 }}>
      <Select label="Period" value={days} onChange={(v: number) => setDays(v)} options={[7, 14, 30, 60].map((n) => ({ value: n, label: `Last ${n} days` }))} />
      <ErrorText>{err}</ErrorText>
      {!d ? (err ? <Button title="Try again" kind="ghost" onPress={load} /> : <ActivityIndicator color={colors.accent} style={{ marginTop: 20 }} />) : (<>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10, marginVertical: 14 }}>
          {([["Model calls", nf(d.totals.calls)], ["Tokens", fmtTokens(d.totals.quota_tokens)], ["Estimated cost", fmtUsd(d.totals.cost_micro_usd)], ["Failed", nf(d.totals.errors)]] as [string, string][]).map(([l, v]) => (
            <Card key={l} style={{ flexBasis: "47%", flexGrow: 1, marginBottom: 0, padding: 12 }}><Text style={{ fontSize: 22, fontWeight: "700", color: colors.ink }}>{v}</Text><Muted>{l}</Muted></Card>
          ))}
        </View>
        <StackedColumns title="Tokens per day" note="By what the call was for. Days are UTC." buckets={d.buckets}
          series={shown.map((p) => ({ key: p, label: PURPOSE_LABEL[p], color: purposeColor(p) }))} />
        <StackedColumns title="Estimated cost per day" note="US dollars, from the price table in Settings." format={fmtUsd}
          buckets={d.buckets.map((b: any) => ({ ...b, parts: { cost: b.cost } }))} series={[{ key: "cost", label: "Cost", color: "#2a78d6" }]} />
        <RankedBars title="Heaviest users" note="Tokens in this period." format={fmtTokens}
          rows={d.top.map((u: any) => ({ label: u.display_name || u.email || String(u.user_id).slice(0, 6), value: u.quota_tokens, tip: `${u.email} · ${nf(u.calls)} calls · ${fmtUsd(u.cost_micro_usd)}` }))} />
        <H2>Latest calls</H2>
        {d.calls.length ? d.calls.map((c: any) => (
          <View key={c.id ?? c.created_at + c.purpose} style={{ paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.line }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Text style={{ color: colors.ink, flex: 1 }}>{PURPOSE_LABEL[c.purpose] || c.purpose}</Text>
              <Tag tone={c.status === "ok" ? "on" : "off"}>{c.status + (c.error_code && c.status !== "ok" ? ": " + c.error_code : "")}</Tag>
            </View>
            <Muted>{`${ago(c.created_at)} · ${c.model || ""} · ${nf(c.quota_tokens)} tokens · ${fmtUsd(c.cost_micro_usd)} · ${c.latency_ms} ms`}</Muted>
          </View>
        )) : <Muted>No calls yet. Calls appear here as soon as someone translates or analyses text.</Muted>}
      </>)}
    </ScrollView>
  );
}

// ------------------------------------------------------------------ activity log
function AuditTab() {
  const { api } = useSession();
  const [rows, setRows] = useState<any[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(async () => { setErr(null); try { setRows((await api.get<{ entries: any[] }>("/api/admin/audit?limit=200")).entries); } catch (e) { setErr(errorText(e)); setRows([]); } }, [api]);
  useEffect(() => { load(); }, [load]);
  return (
    <FlatList data={rows ?? []} keyExtractor={(e: any, i: number) => e.id ?? String(i)} contentContainerStyle={{ padding: 20, paddingTop: 4 }}
      ListHeaderComponent={<ErrorText>{err}</ErrorText>} ListEmptyComponent={rows ? <Muted>Nothing logged yet.</Muted> : <ActivityIndicator color={colors.accent} />}
      renderItem={({ item: e }: any) => (
        <View style={{ paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.line }}>
          <Text style={{ color: colors.ink, fontWeight: "600" }}>{e.action}</Text>
          <Muted>{`${when(e.created_at)} · ${(e.target_type || "")} ${(e.target_id || "").slice(0, 8)}`}</Muted>
          {auditDetail(e.detail) ? <Muted>{auditDetail(e.detail)}</Muted> : null}
        </View>
      )} />
  );
}

// ------------------------------------------------------------------ settings
function SettingsTab() {
  const { api } = useSession();
  const [s, setS] = useState<any>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [planText, setPlanText] = useState<Record<string, Record<string, string>>>({});
  const [cap, setCap] = useState(""), [prices, setPrices] = useState("");
  const [test, setTest] = useState(""), [testOut, setTestOut] = useState<{ ok: boolean; text: string } | null>(null);
  const [err, setErr] = useState<string | null>(null), [ok, setOk] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [st, p] = await Promise.all([api.get<any>("/api/admin/settings"), api.get<{ plans: any[] }>("/api/admin/plans")]);
      setS(st); setPlans(p.plans); setCap(st["llm.global_tokens_per_day"] == null ? "" : String(st["llm.global_tokens_per_day"]));
      setPrices(JSON.stringify(st["llm.prices"] || {}, null, 2));
      setPlanText(Object.fromEntries(p.plans.map((pl: any) => [pl.name, Object.fromEntries(LIMITS.map(([k]) => [k, limitText(pl[k])]))])));
    } catch (e) { setErr(errorText(e)); }
  }, [api]);
  useEffect(() => { load(); }, [load]);

  const save = async (obj: Record<string, unknown>, done = "Saved") => {
    setErr(null); setOk(null);
    try { await api.put("/api/admin/settings", obj); setOk(done); setS((x: any) => ({ ...x, ...obj })); } catch (e) { setErr(errorText(e)); }
  };
  const guard = async (f: () => Promise<void>) => { try { await f(); } catch (e) { setErr(errorText(e)); setOk(null); } };

  if (!s) return <View style={{ padding: 20 }}>{err ? <ErrorText>{err}</ErrorText> : <ActivityIndicator color={colors.accent} />}</View>;
  const toggle = (key: string, label: string, hint: string) => <View key={key}><Check label={label} value={!!s[key]} onChange={(v) => save({ [key]: v })} /><Muted style={{ marginBottom: 8 }}>{hint}</Muted></View>;
  return (
    <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 4, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
      <ErrorText>{err}</ErrorText><OkText>{ok}</OkText>
      <H2>Access and safety</H2>
      {toggle("registration.open", "Anyone can create an account", "Turn off to close sign-ups. Existing users keep access.")}
      {toggle("llm.require_verified_email", "Model features need a confirmed email address", "When on, people who have not clicked the link in their confirmation email can still forge and read languages, but cannot translate or analyse text. Needs email sending to be set up.")}
      {toggle("llm.enabled", "Language model calls are on", "The emergency stop: turning this off blocks every model call, for everyone, at once.")}
      {toggle("llm.store_previews", "Keep a short preview of each model call in the log", "Stores the first 500 characters of the prompt and reply, which may include user text.")}

      <H2>Spending cap</H2>
      <Field label="Most tokens all users together may use per day (UTC)" value={cap} onChangeText={setCap} keyboardType="number-pad" placeholder="No cap" />
      <Button title="Save cap" onPress={() => guard(() => save({ "llm.global_tokens_per_day": parseCap(cap) }, "Cap saved"))} />

      <H2>Plans</H2>
      <Muted style={{ marginBottom: 8 }}>Defaults for everyone on a plan. Blank means no limit. Individual users can be overridden from the Users tab.</Muted>
      {plans.map((p) => (
        <Card key={p.name}>
          <Text style={{ fontWeight: "700", color: colors.ink, fontSize: 16 }}>{p.name}</Text>
          <Muted style={{ marginBottom: 8 }}>{p.description}</Muted>
          {LIMITS.map(([k, l]) => (
            <Field key={k} label={l} value={planText[p.name]?.[k] ?? ""} keyboardType="number-pad" placeholder="none"
              onChangeText={(v: string) => setPlanText({ ...planText, [p.name]: { ...planText[p.name], [k]: v } })} />
          ))}
          <Button title="Save plan" kind="ghost" onPress={() => guard(async () => { await api.put(`/api/admin/plans/${p.name}`, parsePlanLimits(planText[p.name])); setOk("Plan saved"); setErr(null); })} />
        </Card>
      ))}

      <H2>Model prices</H2>
      <Muted style={{ marginBottom: 8 }}>{'US dollars per million tokens, by model name: {"model-name": {"in": 3, "out": 15, "cache_write": 3.75, "cache_read": 0.3}}. Built-in prices are estimates; enter the real ones here.'}</Muted>
      <Field label="Prices (JSON)" value={prices} onChangeText={setPrices} multiline autoCapitalize="none" autoCorrect={false} />
      <Button title="Save prices" onPress={() => guard(() => save({ "llm.prices": parsePrices(prices) }, "Prices saved"))} />

      <H2>Try the model</H2>
      <Muted style={{ marginBottom: 8 }}>Sends one short message through the same metered path as everything else. It shows up in the usage log as Admin test.</Muted>
      <Field label="Message" value={test} onChangeText={setTest} placeholder="Say hello in one sentence" />
      <Button title="Send" onPress={async () => {
        try { const r = await api.post<any>("/api/admin/llm-test", { prompt: test || "Say hello in one sentence." }); setTestOut({ ok: true, text: `${r.text}\n${r.model} · ${r.input_tokens} in, ${r.output_tokens} out · ${fmtUsd(r.cost_micro_usd)}` }); }
        catch (e) { setTestOut({ ok: false, text: errorText(e) }); }
      }} />
      {testOut ? (testOut.ok ? <OkText>{testOut.text}</OkText> : <ErrorText>{testOut.text}</ErrorText>) : null}
    </ScrollView>
  );
}
