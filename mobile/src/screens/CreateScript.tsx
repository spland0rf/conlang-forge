// Making a new writing system: choose how it should look (surprise me, a description, a picture, with some settings fixed)
// BEFORE it is created; the editor then opens on the result. Mirrors the website's "Create a writing system" panel.
import React, { useEffect, useState } from "react";
import { Image, KeyboardAvoidingView, Platform, ScrollView, Text, View } from "react-native";
import { errorText } from "../format";
import { analyzePicture, pickPicture, type Picked } from "../picture";
import { createScriptBody, HOW_OPTIONS, type HowToMake, stepFor, tweakDials } from "../scriptsModel";
import { useSession } from "../session";
import type { LanguageSummary, Proposals, ScriptCatalog, ScriptRecord } from "../types";
import { Button, Card, Check, ErrorText, Field, H1, Muted, Segmented, Select, Stepper } from "../ui/components";
import { colors } from "../ui/theme";

export default function CreateScript({ method, presetLanguage, onBack, onCreated }: {
  method: HowToMake; presetLanguage?: string; onBack: () => void; onCreated: (id: string) => void;
}) {
  const { api } = useSession();
  const [cat, setCat] = useState<ScriptCatalog | null>(null);
  const [languages, setLanguages] = useState<LanguageSummary[]>([]);
  const [how, setHow] = useState<HowToMake>(method);
  const [name, setName] = useState(""), [seed, setSeed] = useState(""), [language, setLanguage] = useState(presetLanguage ?? "");
  const [words, setWords] = useState("");
  const [picked, setPicked] = useState<Picked | null>(null);
  const [tweaks, setTweaks] = useState<Record<string, string | number>>({});
  const [more, setMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const [c, l] = await Promise.all([api.get<ScriptCatalog>("/api/script/dials"), api.get<{ conlangs: LanguageSummary[] }>("/api/conlangs")]);
        if (live) { setCat(c); setLanguages(l.conlangs); }
      } catch (e) { if (live) setErr(errorText(e)); }
    })();
    return () => { live = false; };
  }, [api]);

  const setTweak = (key: string, v: string | number | undefined) => setTweaks((t) => { const n = { ...t }; if (v === undefined || v === "") delete n[key]; else n[key] = v; return n; });
  const choose = async () => { try { const p = await pickPicture(); if (p) setPicked(p); } catch (e) { setErr(errorText(e)); } };

  async function create() {
    if (!cat) return;
    setErr(null);
    let proposals: Proposals | null = null;
    setBusy(true);
    try {
      if (how === "words") {
        if (!words.trim()) throw new Error("Write a few words about the look first.");
        proposals = await api.post<Proposals>("/api/scripts/interpret", { text: words });
      } else if (how === "picture") {
        if (!picked) throw new Error("Choose a picture first.");
        proposals = await api.post<Proposals>("/api/scripts/interpret-image", await analyzePicture(picked));
      }
      const { body, error } = createScriptBody({ name, seed, language, tweaks, proposals: proposals?.proposals });
      if (error || !body) throw new Error(error);
      const made = await api.post<{ script_record: ScriptRecord }>("/api/scripts", body);
      onCreated(made.script_record.id);
    } catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  }

  const langOptions = [{ value: "", label: "No language (a free-standing script)" }, ...languages.map((l) => ({ value: l.id, label: l.name }))];
  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 56, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Text accessibilityRole="button" onPress={onBack} style={{ color: colors.accent, fontSize: 16, marginBottom: 6 }}>‹ Writing systems</Text>
        <H1>Create a writing system</H1>
        <Muted style={{ marginBottom: 12 }}>Choose how it should look. You can change any of it afterwards.</Muted>
        <Segmented options={HOW_OPTIONS} value={how} onChange={(v) => { setHow(v as HowToMake); setErr(null); }} />

        {how === "words" ? (
          <Card>
            <Field label="Describe the look you want" value={words} onChangeText={setWords} multiline maxLength={1500}
              placeholder={'e.g. "Lots of vertical and diagonal lines and slashes, with circles as diacritical marks. It should rise from a solid baseline."'} />
            <Muted>Your words are turned into settings, which you can review and change afterwards.</Muted>
          </Card>
        ) : null}
        {how === "picture" ? (
          <Card>
            <Muted style={{ marginBottom: 8 }}>Choose a picture of sample letters whose style you like. It is shrunk on your phone, read once, and not kept. The letters are not copied; the picture only steers the style settings.</Muted>
            <View style={{ flexDirection: "row", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <Button title={picked ? "Choose another" : "Choose a picture"} kind="ghost" onPress={choose} />
              {picked ? <Image source={{ uri: picked.uri }} style={{ width: 56, height: 56, borderRadius: 6, borderWidth: 1, borderColor: colors.line }} accessibilityLabel="The chosen picture" /> : null}
            </View>
          </Card>
        ) : null}

        <Field label="Name" value={name} onChangeText={setName} maxLength={80} placeholder="Leave blank to name it for you" />
        <Muted style={{ marginBottom: 4 }}>Designed for</Muted>
        <View style={{ marginBottom: 12 }}><Select label="Designed for" value={language} onChange={(v: string) => setLanguage(v)} options={langOptions} /></View>
        <Field label="Seed" value={seed} onChangeText={setSeed} keyboardType="number-pad" placeholder="Random" />

        <Text accessibilityRole="button" onPress={() => setMore(!more)} style={{ color: colors.accent, fontSize: 15, marginVertical: 8 }}>
          {more ? "▾ Shape the writing system (optional)" : "▸ Shape the writing system (optional)"}
        </Text>
        {more && cat ? tweakDials(cat).map((d) => (
          <View key={d.key} style={{ marginBottom: 12 }}>
            <Text style={{ color: colors.muted, fontSize: 13, marginBottom: 4 }}>{d.label}</Text>
            {d.type === "choice"
              ? <Select label={d.label} value={String(tweaks[d.key] ?? "")} onChange={(v: string) => setTweak(d.key, v)}
                  options={[{ value: "", label: "Surprise me" }, ...(d.values || []).map((v) => ({ value: v, label: v }))]} />
              : <>
                  <Check label={`Set ${d.label.toLowerCase()} (otherwise the seed chooses)`} value={d.key in tweaks}
                    onChange={(on) => setTweak(d.key, on ? ((d.min ?? 0) + (d.max ?? 1)) / 2 : undefined)} />
                  {d.key in tweaks ? <Stepper value={Number(tweaks[d.key])} min={d.min ?? 0} max={d.max ?? 1} step={stepFor(d)} onChange={(v) => setTweak(d.key, v)} /> : null}
                </>}
          </View>
        )) : null}
        {more ? <Muted style={{ marginBottom: 8 }}>The remaining settings are in the editor once it is created.</Muted> : null}

        <ErrorText>{err}</ErrorText>
        {busy ? <Muted style={{ marginBottom: 8 }}>{how === "random" ? "Designing…" : how === "words" ? "Reading your description…" : "Looking at the picture…"}</Muted> : null}
        <Button title="Create writing system" onPress={create} busy={busy} disabled={!cat} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
