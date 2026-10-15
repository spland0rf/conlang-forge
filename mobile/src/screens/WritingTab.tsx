// The language's Writing tab: its text written in its primary writing system, or in any other of the user's systems,
// in which case each sound the system lacks is written with its closest sound. Mirrors the website's Writing tab.
import React, { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import { errorText } from "../format";
import { useSession } from "../session";
import type { LanguageScripts, RenderResult, ScriptDetail, ScriptRecord } from "../types";
import { Button, Card, ErrorText, Field, H2, Muted, Select } from "../ui/components";
import { WrittenImage } from "../ui/Download";
import { SvgView } from "../ui/SvgView";
import { colors } from "../ui/theme";

const optionLabel = (s: ScriptRecord, langId: string, primaryId: string | null) =>
  s.name + (s.id === primaryId ? " (primary)" : "") + (s.conlang_id === langId ? "" : s.conlang_name ? ` · made for ${s.conlang_name}` : " · free-standing");

function Result({ r }: { r: RenderResult }) {
  const [open, setOpen] = useState(false);
  const c = r.coverage, rows = c.approximate;
  return (
    <View>
      {r.sentences.length ? r.sentences.map((s, i) => <View key={i} style={{ marginBottom: 6 }}><SvgView xml={s.svg} /></View>) : <Muted>No letters to draw.</Muted>}
      <Muted style={{ marginTop: 6 }}>
        {r.designed_for_this
          ? `Designed for ${r.language}: every one of its ${c.total} sounds has its own letter.`
          : `Not designed for ${r.language}. ${c.exact} of its ${c.total} sounds have an exact letter; the other ${rows.length} use the closest sound this script has.`}
      </Muted>
      {!r.designed_for_this && rows.length ? (
        <View style={{ marginTop: 6 }}>
          <Pressable accessibilityRole="button" onPress={() => setOpen(!open)}><Text style={{ color: colors.accent }}>{(open ? "▾ " : "▸ ") + "How the missing sounds are written"}</Text></Pressable>
          {open ? rows.map((x, i) => (
            <View key={i} style={{ flexDirection: "row", paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: colors.line }}>
              <Text style={{ width: 44, color: colors.word, fontSize: 16 }}>{x.sound}</Text>
              <Text style={{ width: 20, color: colors.muted }}>→</Text>
              <Text style={{ width: 70, color: colors.word, fontSize: 16 }}>{x.written_as.length ? x.written_as.join(" + ") : "(left out)"}</Text>
              <Text style={{ flex: 1, color: colors.muted, fontSize: 13 }}>{x.how}</Text>
            </View>
          )) : null}
        </View>
      ) : null}
      {r.svg ? <View style={{ marginTop: 12 }}><WrittenImage svg={r.svg} name={r.language} /></View> : null}
    </View>
  );
}

export default function WritingTab({ lang, onEditScript, refreshKey = 0 }: { lang: { id: string; name: string }; onEditScript: (id: string | null, languageId?: string) => void; refreshKey?: number }) {
  const { api } = useSession();
  const [primary, setPrimary] = useState<ScriptDetail | null>(null);
  const [list, setList] = useState<LanguageScripts | null>(null);
  const [sel, setSel] = useState<string>("");
  const [cur, setCur] = useState<ScriptDetail | null>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<RenderResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showLetters, setShowLetters] = useState(false);
  const sample = useRef("");

  const load = useCallback(async () => {
    setErr(null);
    try {
      const p = await api.post<ScriptDetail>(`/api/conlangs/${lang.id}/scripts/primary`, {});
      const l = await api.get<LanguageScripts>(`/api/conlangs/${lang.id}/scripts`);
      setPrimary(p); setList(l); setSel(l.primary_id || p.script_record.id); setCur(p);
      sample.current = (p.sentences || []).map((s) => s.text).join(" ");
      setText((t) => t || sample.current);
      return sample.current;
    } catch (e) { setErr(errorText(e)); return ""; }
  }, [api, lang.id]);
  useEffect(() => { load().then((t) => { if (t) write(t); }); /* eslint-disable-next-line */ }, [load, refreshKey]);

  const write = async (value: string, script?: string) => {
    if (!value.trim()) { setResult(null); return; }
    setBusy(true); setErr(null);
    try { setResult(await api.post<RenderResult>(`/api/conlangs/${lang.id}/render`, { text: value, script_id: script || sel || undefined })); }
    catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  };

  const choose = async (id: string) => {
    setSel(id);
    try { setCur(primary && id === primary.script_record.id ? primary : await api.get<ScriptDetail>(`/api/scripts/${id}`)); } catch (e) { setErr(errorText(e)); }
    await write(text, id);
  };

  const makePrimary = async (rec: ScriptRecord) => {
    try { await api.put(`/api/conlangs/${lang.id}/primary-script`, { script_id: rec.id }); await load(); await write(text, rec.id); }
    catch (e) { setErr(errorText(e)); }
  };

  if (!list || !primary) return err ? <View><ErrorText>{err}</ErrorText><Button title="Try again" kind="ghost" onPress={load} /></View> : <View style={{ padding: 20 }}><ActivityIndicator color={colors.accent} /></View>;
  const ordered = [...list.scripts].sort((a, b) => Number(b.id === list.primary_id) - Number(a.id === list.primary_id));
  const rec = cur ? cur.script_record : primary.script_record;
  return (
    <View>
      <H2>Write in the language's script</H2>
      <Muted style={{ marginBottom: 10 }}>Each language has a primary writing system with a letter for every one of its sounds. You can also write it in any other writing system you have made; sounds that script lacks use the closest one it has.</Muted>
      <Field label="Text of the language to write" value={text} onChangeText={setText} multiline maxLength={4000} placeholder="Type or paste text in this language" autoCapitalize="none" />
      <View style={{ flexDirection: "row", gap: 10, marginBottom: 12 }}>
        <Button title="Write" busy={busy} style={{ flex: 1 }} onPress={() => write(text)} />
        <Button title="Use sample sentences" kind="ghost" onPress={() => { setText(sample.current); write(sample.current); }} />
      </View>
      <Muted style={{ marginBottom: 4 }}>Writing system</Muted>
      <Select label="Writing system" value={sel} onChange={choose} options={ordered.map((s) => ({ value: s.id, label: optionLabel(s, lang.id, list.primary_id) }))} />
      <ErrorText>{err}</ErrorText>
      <View style={{ marginTop: 12 }}>
        {busy && !result ? <ActivityIndicator color={colors.accent} /> : result ? <Result r={result} /> : <Muted>There is nothing to write yet.</Muted>}
      </View>
      <View style={{ gap: 8, marginTop: 16 }}>
        <Button title="Edit this writing system" kind="ghost" onPress={() => onEditScript(rec.id)} />
        <Button title="Design another for this language" kind="ghost" onPress={() => onEditScript(null, lang.id)} />
        {rec.conlang_id === lang.id && !rec.primary ? <Button title="Make it the primary script" onPress={() => makePrimary(rec)} /> : null}
      </View>
      <Pressable accessibilityRole="button" onPress={() => setShowLetters(!showLetters)} style={{ marginTop: 16 }}>
        <Text style={{ color: colors.accent, fontWeight: "600" }}>{(showLetters ? "▾ " : "▸ ") + "Letters of this writing system"}</Text>
      </Pressable>
      {showLetters && cur ? <Card style={{ marginTop: 8 }}><SvgView xml={cur.specimen} /></Card> : null}
    </View>
  );
}
