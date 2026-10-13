import React, { useEffect, useMemo, useRef, useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from "react-native";
import {
  dialsFromConfig, EMPTY_MEASURE, forgeBody, FromSampleResult, latestOnly, Measure, meterFraction, meterText, rollSeed, sampleBody,
  sampleLines, shapedLines,
} from "../createModel";
import { errorText } from "../format";
import { useSession } from "../session";
import type { LanguageSummary } from "../types";
import { Button, Card, Check, ErrorText, Field, H1, H2, Muted, Select } from "../ui/components";
import { colors } from "../ui/theme";

/** Name, seed and the five shaping dials: shared by both ways of making a language. */
function Basics({ name, setName, seed, setSeed, choices, setChoices, showDials }: {
  name: string; setName: (v: string) => void; seed: string; setSeed: (v: string) => void;
  choices: Record<string, string>; setChoices: (c: Record<string, string>) => void; showDials: boolean;
}) {
  const { config } = useSession();
  const dials = useMemo(() => dialsFromConfig(config?.dials), [config]);
  return (
    <View>
      <Field label="Name" value={name} onChangeText={setName} maxLength={40} placeholder="Leave blank to invent one" autoCapitalize="words" />
      <Text style={{ color: colors.muted, fontSize: 13, marginBottom: 4 }}>Seed</Text>
      <View style={{ flexDirection: "row", gap: 8, marginBottom: 12 }}>
        <View style={{ flex: 1 }}>
          <Field label="" value={seed} onChangeText={setSeed} keyboardType="number-pad" placeholder="Random" accessibilityLabel="Seed" />
        </View>
        <Button title="Roll" kind="ghost" onPress={() => setSeed(rollSeed())} style={{ minHeight: 46, marginTop: 0 }} />
      </View>
      <Muted style={{ marginTop: -6, marginBottom: 12 }}>The same seed and settings always give the same language.</Muted>
      {showDials && dials.map((d) => (
        <View key={d.key} style={{ marginBottom: 12 }}>
          <Text style={{ color: colors.muted, fontSize: 13, marginBottom: 4 }}>{d.label}</Text>
          <Select label={d.label} value={choices[d.key] ?? ""} onChange={(v) => setChoices({ ...choices, [d.key]: v })}
            options={[{ value: "", label: "Surprise me" }, ...d.options]} />
        </View>
      ))}
    </View>
  );
}

function Page({ children }: { children: React.ReactNode }) {
  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 16, paddingBottom: 40 }} keyboardShouldPersistTaps="handled">{children}</ScrollView>
    </KeyboardAvoidingView>
  );
}

/** Top-level tab: make a language at random, optionally pinning some settings. */
export function ForgeScreen({ onCreated }: { onCreated: (l: LanguageSummary) => void }) {
  const { api } = useSession();
  const [name, setName] = useState(""), [seed, setSeed] = useState("");
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function forge() {
    setErr(null);
    const { body, error } = forgeBody({ name, seed, choices });
    if (error) { setErr(error); return; }
    setBusy(true);
    try {
      const made = await api.post<LanguageSummary>("/api/conlangs", body);
      setName(""); setSeed(""); setChoices({});
      onCreated(made);
    } catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  }

  return (
    <Page>
      <H1>Forge a new language</H1>
      <Muted style={{ marginBottom: 16 }}>Choose a few settings or just press the button. Anything you leave on "Surprise me" is picked at random.</Muted>
      <Basics name={name} setName={setName} seed={seed} setSeed={setSeed} choices={choices} setChoices={setChoices} showDials />
      <ErrorText>{err}</ErrorText>
      {busy && <Muted style={{ marginBottom: 8 }}>Forging… choosing sounds, building roots and writing 2,000 words. This takes a few seconds.</Muted>}
      <Button title="Forge language" onPress={forge} busy={busy} />
    </Page>
  );
}

/** Top-level tab: paste text in the sound you want; the language is shaped to match it. */
export function SampleScreen({ onCreated }: { onCreated: (l: LanguageSummary) => void }) {
  const { api, config } = useSession();
  const modelAvailable = !!config?.model_available;
  const [sample, setSample] = useState("");
  const [name, setName] = useState(""), [seed, setSeed] = useState("");
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [readGrammar, setReadGrammar] = useState(modelAvailable);
  const [more, setMore] = useState(false);
  const [measure, setMeasure] = useState<Measure>(EMPTY_MEASURE);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<FromSampleResult | null>(null);
  const guard = useRef(latestOnly<Measure>()).current;
  useEffect(() => { setReadGrammar(modelAvailable); }, [modelAvailable]);

  useEffect(() => {          // measure the sample 300 ms after the last keystroke; ignore answers that arrive late
    const texts = sampleLines(sample);
    if (!texts.length) { setMeasure(EMPTY_MEASURE); return; }
    const mine = guard.next();
    const t = setTimeout(async () => {
      try { const m = await api.post<Measure>("/api/sample/measure", { texts }); if (guard.isLatest(mine)) setMeasure(m); } catch { /* the meter is a nicety */ }
    }, 300);
    return () => clearTimeout(t);
  }, [sample, api, guard]);

  async function forge() {
    setErr(null);
    const { body, error } = sampleBody({ sample, name, seed, choices, readGrammar, modelAvailable });
    if (error) { setErr(error); return; }
    setBusy(true);
    try {
      const made = await api.post<FromSampleResult>("/api/conlangs/from-sample", body);
      setDone(made);
    } catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  }

  if (done) {
    const l = shapedLines(done.shaped);
    return (
      <Page>
        <H1>Your language is ready</H1>
        <Card>
          <Text style={{ fontSize: 16, color: colors.ink, marginBottom: 6 }}>{l.headline}</Text>
          {l.applied.map((t, i) => <Muted key={i} style={{ marginBottom: 4 }}>{"• " + t}</Muted>)}
          {l.kept.length > 0 && <Text style={{ fontSize: 15, color: colors.ink, marginTop: 10, marginBottom: 6 }}>The sample suggested these, but you had fixed them, so your choice stands:</Text>}
          {l.kept.map((t, i) => <Muted key={i} style={{ marginBottom: 4 }}>{"• " + t}</Muted>)}
          <Muted style={{ marginTop: 10 }}>Everything else was chosen at random, as usual. You can change any of it in the Settings tab.</Muted>
          {l.notes.map((t, i) => <Muted key={i} style={{ marginTop: 6 }}>{t}</Muted>)}
        </Card>
        <Button title={"Open " + done.name} onPress={() => { const d = done; setDone(null); setSample(""); setName(""); setSeed(""); setChoices({}); onCreated(d); }} />
      </Page>
    );
  }

  return (
    <Page>
      <H1>Start from a sample</H1>
      <Muted style={{ marginBottom: 16 }}>The sounds and grammar are worked out from your text. Anything you fix below stays as you set it; whatever the sample cannot tell is chosen at random.</Muted>
      <Field label="Sample text" value={sample} onChangeText={setSample} multiline maxLength={20000} autoCapitalize="none" autoCorrect={false}
        placeholder={"Paste words or sentences that sound the way you want, one per line. Add a meaning after a | if you like.\nkorash vael tume | the old road"} />
      <View accessibilityRole="progressbar" accessibilityLabel="Sample text length in syllables" accessibilityValue={{ min: 0, max: measure.target, now: Math.min(measure.syllables, measure.target) }}
        style={{ height: 8, borderRadius: 4, backgroundColor: colors.line, overflow: "hidden", marginBottom: 6 }}>
        <View style={{ width: `${Math.round(meterFraction(measure) * 100)}%`, height: 8, backgroundColor: measure.level === "good" ? colors.ok : measure.level === "partial" ? colors.warn : colors.muted }} />
      </View>
      <Muted style={{ marginBottom: 12 }}>{meterText(measure)}</Muted>
      <Check label={modelAvailable ? "Also read the grammar (uses the model)" : "Reading the grammar is not available on this server"} value={readGrammar && modelAvailable}
        onChange={(v) => modelAvailable && setReadGrammar(v)} />
      <Text accessibilityRole="button" onPress={() => setMore(!more)} style={{ color: colors.accent, fontSize: 15, marginVertical: 12 }}>
        {more ? "▾ Name, seed and fixed settings" : "▸ Name, seed and fixed settings (optional)"}
      </Text>
      {more && <Basics name={name} setName={setName} seed={seed} setSeed={setSeed} choices={choices} setChoices={setChoices} showDials />}
      <ErrorText>{err}</ErrorText>
      {busy && <Muted style={{ marginBottom: 8 }}>Reading your sample… working out the sounds and grammar, then building the language.</Muted>}
      <Button title="Forge from sample" onPress={forge} busy={busy} />
    </Page>
  );
}
