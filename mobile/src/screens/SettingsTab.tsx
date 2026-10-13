// The settings editor: every setting of a language, fixed or left random, plus the odds that steer the random ones.
// Nothing here edits words; applying settings rebuilds the vocabulary from the rules.
import React, { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { ActivityIndicator, Modal, Pressable, ScrollView, Text, View } from "react-native";
import { errorText } from "../format";
import { useLanguage } from "../language";
import { useSession } from "../session";
import { SettingsDraft, pct, type Setting, type SettingsPayload } from "../settingsModel";
import { safeName, shareTextFile } from "../share";
import type { Language, LanguageSummary } from "../types";
import { Button, Card, Chips, ErrorText, Field, H2, Muted, Select, Stepper } from "../ui/components";
import { colors } from "../ui/theme";

const DEBUG_PINK = "#d6336c";

export default function SettingsTab({ onOpenLanguage }: { onOpenLanguage(l: LanguageSummary): void }) {
  const { api, me } = useSession();
  const { lang, reload } = useLanguage();
  const [S, setS] = useState<SettingsPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [, bump] = useReducer((x: number) => x + 1, 0);
  const [open, setOpen] = useState<Set<string>>(new Set(["sounds"]));
  const [review, setReview] = useState<null | { changes: any[]; mine: Set<string> }>(null);
  const [mode, setMode] = useState<"replace" | "copy">("replace");
  const [busy, setBusy] = useState(false);
  const [debug, setDebug] = useState<string | null>(null);

  const load = async () => {
    setErr(null);
    try { setS(await api.get<SettingsPayload>(`/api/conlangs/${lang.id}/settings`)); } catch (e) { setErr(errorText(e)); }
  };
  useEffect(() => { load(); }, [lang.id, lang.updated_at]);   // eslint-disable-line react-hooks/exhaustive-deps
  const draft = useMemo(() => (S ? new SettingsDraft(S) : null), [S]);

  if (err && !S) return <View><ErrorText>{err}</ErrorText><Button title="Try again" kind="ghost" onPress={load} /></View>;
  if (!S || !draft) return <ActivityIndicator color={colors.accent} style={{ marginTop: 20 }} />;
  const d = draft;
  const change = (fn: () => void) => { fn(); bump(); };

  // ---------------------------------------------------------------- controls
  const oddsRows = (s: Setting) => {
    const rows = d.oddsRows(s);
    if (!rows.length) return <Muted>Not used right now, because you fixed the exact number. Set that number back to Random to use these odds.</Muted>;
    return (
      <View>
        {rows.map((r) => (
          <View key={r.key} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginVertical: 3 }}>
            <Text style={{ flex: 1, color: colors.ink }}>{r.label}</Text>
            <Stepper value={Math.round(r.w * 1000) / 1000} min={0} max={1000} step={1} onChange={(v) => change(() => d.setOdd(s, r.key, v))} />
            <Text style={{ width: 52, textAlign: "right", color: colors.muted }}>{r.share}%</Text>
          </View>
        ))}
        {d.oddsChanged(s.key) && <Button title="Back to the usual odds" kind="ghost" style={{ minHeight: 38, marginTop: 6 }} onPress={() => change(() => d.resetOdds(s))} />}
      </View>
    );
  };

  const control = (s: Setting) => {
    const k = s.key, v = d.cur(k);
    switch (s.kind) {
      case "enum": return <Select label={s.label} options={s.options || []} value={v} onChange={(x) => change(() => d.setVal(k, x))} />;
      case "bool": return <Select label={s.label} options={[{ value: true, label: s.yes || "Yes" }, { value: false, label: s.no || "No" }]} value={v} onChange={(x) => change(() => d.setVal(k, x))} />;
      case "number": {
        const min = d.numberMin(s);
        return (
          <View>
            <Stepper value={Math.max(v, min)} min={min} max={s.max ?? 100} step={s.step ?? 1} onChange={(x) => change(() => d.setVal(k, s.integer ? Math.round(x) : x))} />
            {s.dynamic_min ? <Muted style={{ marginTop: 4 }}>{`Lowest allowed: ${min}, the least that still gives a unique, consistent vocabulary with your other settings.`}</Muted> : null}
          </View>
        );
      }
      case "text": return <TextSetting value={v} max={s.maxlen} label={s.label} onCommit={(x) => change(() => d.setVal(k, x))} />;
      case "multi": {
        const m = d.multi(s);
        return (
          <View>
            <Chips options={m.options} selected={m.selected} locked={m.locked}
              onToggle={(val, on) => {
                const next = on ? [...m.selected, val] : m.selected.filter((x) => x !== val);
                if (next.length < (s.min || 0)) return;           // keep the minimum
                change(() => d.setVal(k, next));
              }} />
            {k === "morphology.cases" ? <Muted>Leave all extra cases off for a language with no cases.</Muted> : null}
          </View>
        );
      }
      case "weights": {
        const rows = d.weightRows(s);
        return (
          <View>
            {rows.map((r) => (
              <View key={r.value} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginVertical: 3 }}>
                <Text style={{ fontSize: 20, color: colors.word, width: 44 }}>{r.label}</Text>
                <Stepper value={r.pct} min={0} max={100} step={1} suffix="%" onChange={(x) => change(() => d.setWeight(s, r.value, x))} />
              </View>
            ))}
          </View>
        );
      }
      case "clusters": {
        const { sel, options } = d.clusterOptions(s);
        if (!options.length) return <Muted>No pairs are possible with the current consonants.</Muted>;
        return (
          <View>
            {s.unused ? <Muted style={{ marginBottom: 6 }}>{s.unused}</Muted> : null}
            <Chips options={options} selected={sel} onToggle={(val, on) => change(() => d.setVal(k, on ? [...sel, val] : sel.filter((x) => x !== val)))} />
          </View>
        );
      }
      case "odds": return oddsRows(s);
      case "tune": {
        const t = d.tuneValue(s);
        return (
          <View>
            <Stepper value={t.value} min={s.min ?? 0} max={s.max ?? 100} step={s.step ?? 1} onChange={(x) => change(() => d.setTune(s, x))} />
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginTop: 4 }}>
              <Muted>{`Usual value: ${s.default}`}</Muted>
              {t.custom ? <Text accessibilityRole="button" style={{ color: colors.accent }} onPress={() => change(() => d.setTune(s, s.default ?? 0))}>Reset</Text> : null}
            </View>
          </View>
        );
      }
      case "rate": {
        const r = d.rateValue(s.key, s.default ?? 0);
        return (
          <View>
            <Stepper value={Math.round(r.value * 100)} min={0} max={100} step={1} suffix="%" onChange={(x) => change(() => d.setRate(s.key, s.default ?? 0, x))} />
            <Muted style={{ marginTop: 4 }}>{`Chance, in percent. Usual: ${Math.round((s.default ?? 0) * 100)}%`}</Muted>
          </View>
        );
      }
      default: return <Text>{String(v)}</Text>;
    }
  };

  const oddsBox = (s: Setting) => {
    if (d.hasOddsBox(s)) {
      const changed = d.oddsChanged(s.key);
      return (
        <Collapsible title={"Odds when random" + (changed ? " (changed)" : "")} startOpen={changed}>
          <Muted style={{ marginBottom: 6 }}>Relative weights; they do not need to add up to anything. They only matter while this setting is on Random.</Muted>
          {oddsRows({ ...s, kind: "odds" })}
        </Collapsible>
      );
    }
    if (s.chance) {
      const r = d.rateValue(s.key, s.chance.default);
      return (
        <Collapsible title={`Chance of "yes" when random: ${Math.round(r.value * 100)}%` + (r.custom ? " (changed)" : "")} startOpen={r.custom}>
          <Stepper value={Math.round(r.value * 100)} min={0} max={100} step={1} suffix="%" onChange={(x) => change(() => d.setRate(s.key, s.chance!.default, x))} />
        </Collapsible>
      );
    }
    return null;
  };

  const row = (s: Setting) => {
    const editable = "editable" in s, k = s.key, fixed = editable && d.pinned(k);
    const lockable = editable && !["odds", "rate", "tune"].includes(s.kind);
    return (
      <View key={k} style={{ paddingVertical: 10, borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: d.touched(k) ? "#fff8e6" : "transparent", marginHorizontal: -4, paddingHorizontal: 4 }}>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <Text style={{ flex: 1, fontSize: 16, fontWeight: "600", color: colors.ink }}>{s.label}</Text>
          {lockable && (
            <Pressable accessibilityRole="button" accessibilityLabel={fixed ? "Fixed. Tap to leave it random." : "Random. Tap to fix it at its current value."} onPress={() => change(() => d.lock(k))}
              style={{ paddingVertical: 5, paddingHorizontal: 12, borderRadius: 14, backgroundColor: fixed ? colors.accent : "#e6f0ec" }}>
              <Text style={{ color: fixed ? colors.accentInk : colors.accent, fontWeight: "600", fontSize: 13 }}>{fixed ? "Fixed" : "Random"}</Text>
            </Pressable>
          )}
        </View>
        <Muted style={{ marginVertical: 4 }}>{s.help}</Muted>
        {control(s)}
        {lockable ? oddsBox(s) : null}
      </View>
    );
  };

  // ---------------------------------------------------------------- review and apply
  const startReview = async () => {
    setErr(null); setBusy(true);
    try {
      const pre = await api.post<{ changes: any[] }>(`/api/conlangs/${lang.id}/settings/preview`, d.payload());
      setMode("replace");
      setReview({ changes: pre.changes, mine: new Set([...Object.keys(d.set), ...d.unpin]) });
    } catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  };
  const apply = async () => {
    setBusy(true); setErr(null);
    try {
      const res = await api.post<{ id: string }>(`/api/conlangs/${lang.id}/settings/apply`, { ...d.payload(), mode });
      setReview(null);
      if (mode === "copy") { const l = await api.get<Language>(`/api/conlangs/${res.id}`); onOpenLanguage(l); }
      else { await reload(); await load(); }
    } catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  };
  const showDebug = async () => {
    try { setDebug(JSON.stringify(await api.get(`/api/conlangs/${lang.id}/debug/settings`), null, 2)); } catch (e) { setErr(errorText(e)); }
  };

  const n = d.changeCount();
  return (
    <View style={{ flex: 1 }}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ paddingBottom: n ? 90 : 30 }}>
        {me?.debug ? <Button title="Debug: show settings" style={{ backgroundColor: DEBUG_PINK, marginBottom: 12 }} onPress={showDebug} /> : null}
        <Muted style={{ marginBottom: 10 }}>Fix a setting to hold it still, or leave it on Random and the generator picks it from the odds. Applying rebuilds the vocabulary by the rules; it never edits a word by hand.</Muted>
        <ErrorText>{err}</ErrorText>
        {S.groups.map((g) => {
          const items = S.settings.filter((s) => s.group === g.id);
          const edited = items.filter((s) => "editable" in s && d.touched(s.key)).length;
          const isOpen = open.has(g.id) || edited > 0;
          return (
            <Card key={g.id} style={{ paddingVertical: 8 }}>
              <Pressable accessibilityRole="button" accessibilityState={{ expanded: isOpen }} style={{ flexDirection: "row", alignItems: "center", paddingVertical: 8 }}
                onPress={() => setOpen((o) => { const x = new Set(o); x.has(g.id) ? x.delete(g.id) : x.add(g.id); return x; })}>
                <Text style={{ flex: 1, fontSize: 17, fontWeight: "700", color: colors.ink }}>{g.label}</Text>
                {edited ? <Text style={{ color: colors.warn, marginRight: 10 }}>{edited} changed</Text> : null}
                <Text style={{ color: colors.muted }}>{isOpen ? "▴" : "▾"}</Text>
              </Pressable>
              {isOpen && (<><Muted style={{ marginBottom: 6 }}>{g.help}</Muted>{items.map(row)}</>)}
            </Card>
          );
        })}
      </ScrollView>

      {n > 0 && (
        <View style={{ position: "absolute", left: 0, right: 0, bottom: 0, backgroundColor: colors.card, borderTopWidth: 1, borderTopColor: colors.line, padding: 12 }}>
          <Text style={{ color: colors.ink, marginBottom: 8 }}>{`${n} change${n === 1 ? "" : "s"} not applied yet`}</Text>
          <View style={{ flexDirection: "row", gap: 10 }}>
            <Button title="Discard" kind="ghost" style={{ flex: 1 }} onPress={() => change(() => d.discard())} />
            <Button title="Review and apply" busy={busy} style={{ flex: 2 }} onPress={startReview} />
          </View>
        </View>
      )}

      <Modal visible={!!review} animationType="slide" onRequestClose={() => setReview(null)}>
        <View style={{ flex: 1, backgroundColor: colors.bg, paddingTop: 56, paddingHorizontal: 20 }}>
          <H2>Review changes</H2>
          <ScrollView style={{ flex: 1 }}>
            {review && review.changes.length === 0 && <Muted>None of the visible settings change. The words may still be redrawn if odds or tendencies changed.</Muted>}
            {review?.changes.map((c) => (
              <View key={c.key} style={{ paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.line }}>
                <Text style={{ fontWeight: "700", color: colors.ink }}>{c.label}{review.mine.has(c.key) ? "" : <Text style={{ fontWeight: "400", color: colors.muted }}> (follows from your changes)</Text>}</Text>
                <Text style={{ color: colors.muted }}>{String(c.before)}</Text>
                <Text style={{ color: colors.ink }}>→ {String(c.after)}</Text>
              </View>
            ))}
            <View style={{ marginTop: 16 }}>
              {([["replace", "Rebuild this language", "Every word is regenerated from the new settings. The old words are not kept."], ["copy", "Save as a new language", "Keeps this language as it is and creates another one with these settings."]] as const).map(([val, t, desc]) => (
                <Pressable key={val} accessibilityRole="radio" accessibilityState={{ checked: mode === val }} onPress={() => setMode(val)} style={{ flexDirection: "row", gap: 10, paddingVertical: 8 }}>
                  <View style={{ width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: colors.accent, alignItems: "center", justifyContent: "center" }}>
                    {mode === val ? <View style={{ width: 11, height: 11, borderRadius: 6, backgroundColor: colors.accent }} /> : null}
                  </View>
                  <View style={{ flex: 1 }}><Text style={{ fontWeight: "700", color: colors.ink }}>{t}</Text><Muted>{desc}</Muted></View>
                </Pressable>
              ))}
            </View>
          </ScrollView>
          <ErrorText>{err}</ErrorText>
          <View style={{ flexDirection: "row", gap: 10, marginVertical: 16 }}>
            <Button title="Back" kind="ghost" style={{ flex: 1 }} onPress={() => setReview(null)} />
            <Button title={mode === "copy" ? "Save as new" : "Apply"} busy={busy} style={{ flex: 2 }} onPress={apply} />
          </View>
        </View>
      </Modal>

      <Modal visible={debug !== null} animationType="slide" onRequestClose={() => setDebug(null)}>
        <View style={{ flex: 1, backgroundColor: colors.bg, paddingTop: 56, paddingHorizontal: 20 }}>
          <H2>Settings as stored</H2>
          <Muted style={{ marginBottom: 8 }}>Seed, fixed settings and tuning are all that is needed to rebuild this language (rebuild_from).</Muted>
          <ScrollView style={{ flex: 1, backgroundColor: "#fff", borderRadius: 8 }}><Text selectable style={{ fontFamily: "monospace", fontSize: 11, padding: 8, color: colors.ink }}>{debug}</Text></ScrollView>
          <View style={{ flexDirection: "row", gap: 10, marginVertical: 16 }}>
            <Button title="Share .json" kind="ghost" style={{ flex: 1 }} onPress={() => shareTextFile(`${safeName(lang.name)}-${lang.seed}-settings.json`, debug || "", "application/json")} />
            <Button title="Close" style={{ flex: 1 }} onPress={() => setDebug(null)} />
          </View>
        </View>
      </Modal>
    </View>
  );
}

function Collapsible({ title, startOpen, children }: { title: string; startOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(!!startOpen);
  return (
    <View style={{ marginTop: 8 }}>
      <Text accessibilityRole="button" onPress={() => setOpen(!open)} style={{ color: colors.accent, fontSize: 14 }}>{(open ? "▾ " : "▸ ") + title}</Text>
      {open ? <View style={{ marginTop: 6 }}>{children}</View> : null}
    </View>
  );
}

function TextSetting({ value, max, label, onCommit }: { value: string; max?: number; label: string; onCommit(v: string): void }) {
  const [t, setT] = useState(value);
  useEffect(() => setT(value), [value]);
  return <Field label={label} value={t} onChangeText={setT} maxLength={max} onEndEditing={() => t.trim() && t.trim() !== value && onCommit(t.trim())} />;
}
