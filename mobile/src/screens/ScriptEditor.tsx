// The writing-system editor: name, the language it is designed for, a seed, and every dial, redrawn after each change.
// Settings can be kept ("pinned") so Randomize leaves them alone; the look can also be described in words or with a
// picture of letters, and the result becomes suggested settings. Mirrors the website's writing-system editor.
import React, { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ActivityIndicator, Alert, Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { errorText } from "../format";
import { pickPicture, analyzePicture, type Picked } from "../picture";
import { ScriptDraft, applyProposals, dialLabel, dialsOf, fmtDial, stepFor } from "../scriptsModel";
import { useSession } from "../session";
import type { BranchResult, LanguageSummary, Proposals, ScriptCatalog, ScriptDetail, ScriptDial, ScriptPreview } from "../types";
import { Button, Card, Check, ErrorText, Field, H1, H2, Muted, Select, Stepper } from "../ui/components";
import { SvgView } from "../ui/SvgView";
import { colors } from "../ui/theme";
import VersionsPanel from "./VersionsPanel";

type Result = ScriptDetail | ScriptPreview;

function DialRow({ d, draft, spec, onChoose, onKeep }: { d: ScriptDial; draft: ScriptDraft; spec: Record<string, any>; onChoose(v: string | number): void; onKeep(): void }) {
  const fixed = draft.fixed(d.key), pinned = draft.pinned(d.key), val = spec[d.key];
  return (
    <View style={{ paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.line, borderLeftWidth: pinned ? 3 : 0, borderLeftColor: "#d9a400", paddingLeft: pinned ? 8 : 0 }}>
      <Text style={{ color: colors.ink, fontWeight: "600", fontSize: 15 }}>{d.label}</Text>
      <Muted style={{ marginBottom: 6 }}>{fixed ? "Set by the language's own sounds" : d.description}</Muted>
      <View style={{ opacity: fixed ? 0.5 : 1 }} pointerEvents={fixed ? "none" : "auto"}>
        {d.type === "choice"
          ? <Select label={d.label} value={String(val)} onChange={(v: string) => onChoose(v)} options={(d.values || []).map((v) => ({ value: v, label: v }))} />
          : <Stepper value={Number(val)} min={d.min ?? 0} max={d.max ?? 1} step={stepFor(d)} onChange={(v) => onChoose(v)} suffix={fixed ? "(from the language)" : undefined} />}
      </View>
      {!fixed ? <Check label={`Keep ${d.label.toLowerCase()} when the seed changes`} value={pinned} onChange={onKeep} /> : null}
    </View>
  );
}

export default function ScriptEditor({ id, presetLanguage, onBack, onChanged, onOpenScript, onOpenLanguage }: {
  id: string | null; presetLanguage?: string; onBack: () => void; onChanged: () => void;
  onOpenScript: (id: string) => void; onOpenLanguage: (l: LanguageSummary) => void;
}) {
  const { api } = useSession();
  const [, bump] = useReducer((x: number) => x + 1, 0);
  const [cat, setCat] = useState<ScriptCatalog | null>(null);
  const [languages, setLanguages] = useState<LanguageSummary[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [saving, setSaving] = useState(false);
  const draft = useRef<ScriptDraft | null>(null);
  const latest = useRef(0);

  // design by description
  const [words, setWords] = useState("");
  const [picked, setPicked] = useState<Picked | null>(null);
  const [asking, setAsking] = useState<null | "text" | "picture">(null);
  const [suggest, setSuggest] = useState<Proposals | null>(null);
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [suggestErr, setSuggestErr] = useState<string | null>(null);
  const [showVersions, setShowVersions] = useState(false);

  const redraw = useCallback(async () => {
    const d = draft.current; if (!d) return;
    const mine = ++latest.current;
    setDrawing(true); setErr(null);
    try {
      const r = await api.post<ScriptPreview>("/api/scripts/preview", d.previewBody());
      if (mine === latest.current) { d.seed = r.seed; setResult(r); }
    } catch (e) { if (mine === latest.current) setErr(errorText(e)); }
    finally { if (mine === latest.current) setDrawing(false); }
  }, [api]);

  useEffect(() => {
    (async () => {
      try {
        const [c, l, saved] = await Promise.all([api.get<ScriptCatalog>("/api/script/dials"), api.get<{ conlangs: LanguageSummary[] }>("/api/conlangs"),
          id ? api.get<ScriptDetail>(`/api/scripts/${id}`) : Promise.resolve(null)]);
        setCat(c); setLanguages(l.conlangs || []);
        const preset = presetLanguage && (l.conlangs || []).some((x) => x.id === presetLanguage) ? presetLanguage : "";
        draft.current = new ScriptDraft(saved ? saved.script_record : null, preset);
        if (saved) setResult(saved); else await redraw();
        bump();
      } catch (e) { setLoadErr(errorText(e)); }
    })();
  }, [api, id, presetLanguage, redraw]);

  const d = draft.current;
  const touch = (run = true) => { bump(); if (run) redraw(); };

  const save = async (): Promise<boolean> => {
    if (!d) return false;
    setSaving(true); setErr(null);
    try {
      const r = d.rec ? await api.put<ScriptDetail>(`/api/scripts/${d.rec.id}`, d.body()) : await api.post<ScriptDetail>("/api/scripts", d.body());
      onChanged();
      if (!d.rec) { onOpenScript(r.script_record.id); return true; }
      d.markSaved(r.script_record); setResult(r); bump();
      return true;
    } catch (e) { setErr(errorText(e)); return false; } finally { setSaving(false); }
  };

  const makePrimary = async () => {
    if (!d) return;
    try {
      if ((d.dirty || !d.rec || d.rec.conlang_id !== d.conlang) && !(await save())) return;
      if (!d.rec) return;                                    // a new system was saved: the editor reopens on it
      const r = await api.put<ScriptDetail>(`/api/conlangs/${d.conlang}/primary-script`, { script_id: d.rec.id });
      d.markSaved(r.script_record); onChanged(); bump();
      Alert.alert("Primary writing system", "This is now the primary writing system for the language.");
    } catch (e) { setErr(errorText(e)); }
  };

  const remove = () => Alert.alert("Delete this writing system?", "Languages written in it will fall back to a newly designed primary script.", [
    { text: "Cancel", style: "cancel" },
    { text: "Delete", style: "destructive", onPress: async () => {
      try { await api.del(`/api/scripts/${d!.rec!.id}`); onChanged(); onBack(); } catch (e) { setErr(errorText(e)); }
    } },
  ]);

  const showProposals = (p: Proposals) => { setSuggest(p); setTicked(new Set(p.proposals.map((x) => x.key))); };
  const askText = async () => {
    if (!words.trim()) { setSuggestErr("Write a few words about the look first."); return; }
    setAsking("text"); setSuggestErr(null); setSuggest(null);
    try { showProposals(await api.post<Proposals>("/api/scripts/interpret", { text: words })); } catch (e) { setSuggestErr(errorText(e)); } finally { setAsking(null); }
  };
  const choosePicture = async () => {
    try { const p = await pickPicture(); if (p) { setPicked(p); setSuggest(null); setSuggestErr(null); } } catch (e) { setSuggestErr(errorText(e)); }
  };
  const askPicture = async () => {
    if (!picked) { setSuggestErr("Choose a picture first."); return; }
    setAsking("picture"); setSuggestErr(null); setSuggest(null);
    try { showProposals(await api.post<Proposals>("/api/scripts/interpret-image", await analyzePicture(picked))); }
    catch (e) { setSuggestErr(errorText(e)); } finally { setAsking(null); }
  };
  const applySelected = () => {
    if (!d || !suggest) return;
    applyProposals(d, suggest.proposals, ticked); setSuggest(null); touch();
  };

  const openCopy = (r: BranchResult) => {
    onChanged();
    if (r.kind === "script") onOpenScript(r.item.script_record.id); else onOpenLanguage(r.item);
  };

  if (loadErr) return <View style={{ flex: 1, backgroundColor: colors.bg, padding: 20, paddingTop: 60 }}><ErrorText>{loadErr}</ErrorText><Button title="Back" kind="ghost" onPress={onBack} /></View>;
  if (!cat || !d || !result) return <View style={{ flex: 1, backgroundColor: colors.bg, justifyContent: "center" }}><ActivityIndicator color={colors.accent} /></View>;

  const spec = result.spec, m = result.metrics || {};
  const langName = languages.find((l) => l.id === d.conlang)?.name;
  const langOptions = [{ value: "", label: "No language (a free-standing script)" }, ...languages.map((l) => ({ value: l.id, label: l.name }))];
  const rec = d.rec;

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView stickyHeaderIndices={[1]} keyboardShouldPersistTaps="handled" contentContainerStyle={{ paddingBottom: 60 }}>
        <View style={{ paddingHorizontal: 20, paddingTop: 56 }}>
          <Text accessibilityRole="button" onPress={onBack} style={{ color: colors.accent, fontSize: 16, marginBottom: 6 }}>‹ Writing systems</Text>
          <H1>{rec ? rec.name : "New writing system"}</H1>
          <Muted style={{ marginBottom: 10 }}>Tick “Keep” beside a setting to hold it: Randomize then changes everything except the kept settings. Choosing a value keeps that setting automatically. Nothing is stored until you press Save. Tying the system to a language gives it a letter for each of that language's sounds.</Muted>
        </View>

        {/* the sample stays in view while the dials below it are changed */}
        <View style={{ backgroundColor: colors.bg, paddingHorizontal: 20, paddingVertical: 6 }}>
          <Card style={{ marginBottom: 0, padding: 8, opacity: drawing ? 0.6 : 1 }}>
            <SvgView xml={result.sample} maxScale={0.7} />
          </Card>
        </View>

        <View style={{ paddingHorizontal: 20, paddingTop: 10 }}>
          <Field label="Name" value={d.name} onChangeText={(v: string) => { d.setName(v); touch(false); }} maxLength={80} placeholder="Name this writing system" />
          <Muted style={{ marginBottom: 4 }}>Designed for</Muted>
          <Select label="Designed for" value={d.conlang} onChange={(v: string) => { d.setLanguage(v); touch(); }} options={langOptions} />
          <View style={{ flexDirection: "row", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
            <Button title="Save" busy={saving} style={{ flex: 1 }} onPress={save} />
            {d.conlang ? <Button title={d.isPrimaryHere() && !d.dirty ? "Primary for this language" : "Make primary"} kind="ghost" disabled={d.isPrimaryHere() && !d.dirty} onPress={makePrimary} /> : null}
          </View>
          <Muted style={{ marginTop: 6 }}>{d.status()}</Muted>
          <ErrorText>{err}</ErrorText>
          {rec ? <Button title="Delete" kind="ghost" style={{ marginTop: 8 }} onPress={remove} /> : null}

          <Card style={{ marginTop: 16 }}>
            <H2>Describe the look</H2>
            <Field label="Describe the look you want" value={words} onChangeText={setWords} multiline maxLength={1500}
              placeholder={'e.g. "Lots of vertical and diagonal lines and slashes, with circles as diacritical marks. It should rise from a solid baseline."'} />
            <Button title="Suggest settings" kind="ghost" busy={asking === "text"} onPress={askText} />
            <Text style={{ fontSize: 16, fontWeight: "600", color: colors.ink, marginTop: 16, marginBottom: 4 }}>Or show a picture</Text>
            <Muted style={{ marginBottom: 8 }}>Choose a picture of sample letters whose style you like. It is shrunk on your phone, read once, and not kept. The letters are not copied; the picture only steers the style settings.</Muted>
            <View style={{ flexDirection: "row", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <Button title={picked ? "Choose another" : "Choose a picture"} kind="ghost" onPress={choosePicture} />
              {picked ? <Image source={{ uri: picked.uri }} style={{ width: 56, height: 56, borderRadius: 6, borderWidth: 1, borderColor: colors.line }} accessibilityLabel="The chosen picture" /> : null}
              <Button title="Suggest from picture" busy={asking === "picture"} disabled={!picked} onPress={askPicture} />
            </View>
            <ErrorText>{suggestErr}</ErrorText>
            {suggest ? (
              <View style={{ marginTop: 10 }}>
                {suggest.proposals.map((p) => (
                  <Check key={p.key} value={ticked.has(p.key)} label={`${dialLabel(cat, p.key)}: ${p.value}${p.evidence ? ` — “${p.evidence}”` : ""}`}
                    onChange={(on) => setTicked((t) => { const n = new Set(t); if (on) n.add(p.key); else n.delete(p.key); return n; })} />
                ))}
                {suggest.proposals.length ? <Button title="Apply selected" style={{ marginTop: 6 }} onPress={applySelected} /> : null}
                {suggest.notes.map((n, i) => <Muted key={i} style={{ marginTop: 4 }}>{n}</Muted>)}
              </View>
            ) : null}
          </Card>

          <Card style={{ marginTop: 4 }}>
            <Muted style={{ marginBottom: 4 }}>Seed</Muted>
            <Stepper value={d.seed} min={0} max={2 ** 31 - 1} step={1} onChange={(v: number) => { d.setSeed(v); touch(); }} />
            <View style={{ flexDirection: "row", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              <Button title="Randomize" onPress={() => { d.randomize(); touch(); }} />
              <Button title="Keep all settings" kind="ghost" onPress={() => { d.keepAll(cat, spec); touch(false); }} />
              <Button title="Release all" kind="ghost" onPress={() => { d.releaseAll(); touch(); }} />
            </View>
            <Muted style={{ marginTop: 8 }}>“Keep all settings” holds every dial at its current value, so Randomize only changes the small details.</Muted>
          </Card>

          {"sentences" in result && result.sentences && result.sentences.length ? (
            <Card>
              <H2>{`Sentences in ${(result as ScriptDetail).language?.name ?? langName ?? "the language"}`}</H2>
              {result.sentences.map((s, i) => <View key={i} style={{ marginBottom: 8 }}><SvgView xml={s.svg} /><Muted>{s.english}</Muted></View>)}
            </Card>
          ) : null}
          <Card>
            <H2>Letters</H2>
            <SvgView xml={result.specimen} />
            <Muted style={{ marginTop: 6 }}>{`${m.letters ?? "?"} letters`}{m.sound_coherence && m.sound_coherence.nearest_same_manner != null ? ` · similar shapes share sounds ${Math.round(m.sound_coherence.nearest_same_manner * 100)}%` : ""}</Muted>
          </Card>

          {cat.groups.map((g) => {
            const ds = dialsOf(cat, g);
            return ds.length ? (
              <Card key={g}>
                <H2>{g}</H2>
                {ds.map((dial) => (
                  <DialRow key={dial.key} d={dial} draft={d} spec={spec}
                    onChoose={(v: string | number) => { d.setPin(dial.key, v); touch(); }}
                    onKeep={() => { d.toggleKeep(dial.key, spec[dial.key]); touch(false); }} />
                ))}
              </Card>
            ) : null;
          })}

          {rec ? (
            <Card>
              <Pressable accessibilityRole="button" onPress={() => setShowVersions(!showVersions)}>
                <Text style={{ fontSize: 18, fontWeight: "600", color: colors.ink }}>{(showVersions ? "▾ " : "▸ ") + "Versions"}</Text>
              </Pressable>
              {showVersions ? <View style={{ marginTop: 10 }}><VersionsPanel kind="script" id={rec.id} prepare={async () => (d.dirty ? await save() : true)} onOpenCopy={openCopy} /></View> : null}
            </Card>
          ) : null}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
