import React, { useEffect, useState } from "react";
import { ActivityIndicator, Text, View } from "react-native";
import { errorText, fmtTokens, tokenCount } from "../format";
import { useLanguage } from "../language";
import { useSession } from "../session";
import { approxNote, defaultWriting, writingOptions } from "../scriptsModel";
import type { FromResult, InterToken, Issue, LanguageScripts, RenderResult, ToResult } from "../types";
import { Button, Card, Check, ErrorText, Field, H2, Muted, Segmented, Select } from "../ui/components";
import { WrittenImage } from "../ui/Download";
import { colors } from "../ui/theme";

const EXAMPLES = ["The old wizard walked into the tavern and ordered a drink.", "Where did the king hide the sword?",
  "We will not surrender the castle to the dragon.", "Please bring me bread and water."];

function Interlinear({ items }: { items: { text: string; gloss: string; known?: boolean }[] }) {
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", marginTop: 6 }}>
      {items.map((it, i) => (
        <View key={i} style={{ marginRight: 12, marginBottom: 8 }}>
          <Text style={{ fontSize: 17, color: it.known === false ? colors.warn : colors.word, fontWeight: "600" }}>{it.text}</Text>
          <Text style={{ fontSize: 12, color: colors.muted }}>{it.gloss}</Text>
        </View>
      ))}
    </View>
  );
}
const inter = (t: InterToken[]) => t.map((x) => ({ text: x.text, gloss: x.gloss + (x.alts?.length ? " / " + x.alts.join(" / ") : ""), known: x.known }));

function Notes({ issues }: { issues: Issue[] }) {
  const shown = (issues || []).filter((i) => i.level !== "info" && i.code !== "tense_unmarked");
  if (!shown.length) return null;
  return (
    <View style={{ marginTop: 6 }}>
      <Text style={{ color: colors.warn, fontWeight: "600" }}>{shown.length} thing{shown.length > 1 ? "s" : ""} to know</Text>
      {shown.map((i, k) => <Muted key={k}>• {i.message}</Muted>)}
    </View>
  );
}


// The optional "Writing system" area under a translation: a chooser and the sentence drawn in the chosen script.
function WritingArea({ lang, text, chosen, setChosen }: { lang: { id: string; name: string }; text: string; chosen: string | null; setChosen: (v: string) => void }) {
  const { api } = useSession();
  const [scripts, setScripts] = useState<LanguageScripts | null>(null);
  const [failed, setFailed] = useState(false);
  const [pic, setPic] = useState<RenderResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { api.get<LanguageScripts>(`/api/conlangs/${lang.id}/scripts`).then(setScripts, () => setFailed(true)); }, [api, lang.id]);
  const options = scripts ? writingOptions(scripts.scripts, scripts.primary_id) : [];
  const value = scripts ? defaultWriting(options, chosen, scripts.primary_id) : "none";

  useEffect(() => {
    if (!scripts || value === "none") { setPic(null); return; }
    let live = true;
    setBusy(true); setErr(null);
    api.post<RenderResult>(`/api/conlangs/${lang.id}/render`, { text, script_id: value })
      .then((r) => { if (live) setPic(r); }, (e) => { if (live) setErr(errorText(e)); })
      .finally(() => { if (live) setBusy(false); });
    return () => { live = false; };
  }, [api, lang.id, text, value, scripts]);

  if (failed || !scripts) return null;
  const n = pic ? pic.approximations.length || pic.coverage.approximate.length : 0;
  return (
    <Card>
      <Muted style={{ marginBottom: 4 }}>Writing system</Muted>
      <Select label="Writing system" value={value} onChange={(v: string) => setChosen(v)} options={options} />
      {value !== "none" ? (
        <View style={{ marginTop: 10 }}>
          <ErrorText>{err}</ErrorText>
          {busy && !pic ? <ActivityIndicator color={colors.accent} /> : pic ? (
            <View>
              {pic.svg ? <WrittenImage svg={pic.svg} name={lang.name} /> : <Muted>Nothing to draw.</Muted>}
              {!pic.designed_for_this && n ? <Muted style={{ marginTop: 6 }}>{approxNote(lang.name, n)}</Muted> : null}
            </View>
          ) : null}
        </View>
      ) : null}
    </Card>
  );
}

export default function TranslateTab({ lang }: { lang: { id: string; name: string } }) {
  const { api, config } = useSession();
  const { script } = useLanguage();
  const modelOn = !!config?.model_available;
  const [dir, setDir] = useState<"to" | "from">("to");
  const [text, setText] = useState("");
  const [smooth, setSmooth] = useState(modelOn);
  const [simple, setSimple] = useState(!modelOn);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [toRes, setToRes] = useState<ToResult | null>(null);
  const [fromRes, setFromRes] = useState<FromResult | null>(null);
  const [edit, setEdit] = useState("");
  const [writing, setWriting] = useState<string | null>(null);      // chosen writing system; kept from one translation to the next

  const run = async (input: string, mode: "english" | "restricted") => {
    if (!input.trim()) { setErr("Enter some text first."); return; }
    setErr(null); setBusy(true); setToRes(null); setFromRes(null);
    try {
      const path = `/api/conlangs/${lang.id}/translate`;
      if (dir === "to") {
        const r = await api.post<ToResult>(path, { direction: "to", text: input, mode, script });
        setToRes(r); setEdit(r.re_text);
      } else {
        setFromRes(await api.post<FromResult>(path, { direction: "from", text: input, smooth: smooth && modelOn }));
      }
    } catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  };

  return (
    <View>
      <Segmented value={dir} onChange={(v) => { setDir(v as "to" | "from"); setToRes(null); setFromRes(null); setErr(null); }}
        options={[["to", "English to " + lang.name], ["from", lang.name + " to English"]]} />
      <Muted style={{ marginBottom: 8 }}>
        {dir === "to"
          ? (modelOn ? "Your text is simplified to the language's vocabulary first, then translated." : "No language model is connected on this server, so write simple English (short sentences, everyday words).")
          : "Paste or type text in this language. Sentences end with . or ?"}
      </Muted>
      <Field label={dir === "to" ? "English text" : lang.name + " text"} value={text} onChangeText={setText} multiline maxLength={4000}
        autoCapitalize="sentences" placeholder={dir === "to" ? "Write anything in English." : ""} />
      {dir === "to" && <Check label="My text is already simple English (no model, free)" value={simple || !modelOn} onChange={setSimple} />}
      {dir === "from" && modelOn && <Check label="Make the English read naturally (uses a few tokens)" value={smooth} onChange={setSmooth} />}
      <ErrorText>{err}</ErrorText>
      <View style={{ flexDirection: "row", gap: 10, marginTop: 6 }}>
        <Button title="Translate" busy={busy} style={{ flex: 1 }} onPress={() => run(text, dir === "to" ? (simple || !modelOn ? "restricted" : "english") : "english")} />
        {dir === "to" && <Button title="Example" kind="ghost" onPress={() => setText(EXAMPLES[Math.floor(Math.random() * EXAMPLES.length)])} />}
      </View>

      {toRes && (
        <View style={{ marginTop: 20 }}>
          <H2>Translation</H2>
          {toRes.sentences.map((s, i) => (
            <View key={i} style={{ marginBottom: 10 }}>
              <Text selectable style={{ fontSize: 22, color: colors.word, fontWeight: "700" }}>{s.text}</Text>
              <Interlinear items={s.forms.map((f, k) => ({ text: f, gloss: s.glosses[k] }))} />
            </View>
          ))}
          <WritingArea lang={lang} text={toRes.text} chosen={writing} setChosen={setWriting} />
          <Muted>{toRes.usage ? `Used ${fmtTokens(tokenCount(toRes.usage))} tokens` : "No tokens used"}</Muted>
          <Notes issues={toRes.issues} />
          <View style={{ marginTop: 16 }}>
            <H2>{toRes.mode === "english" ? "What was translated" : "Your simple English"}</H2>
            <Muted>{toRes.mode === "english" ? "Your text, simplified to this language's vocabulary. Edit it and translate again; that costs no tokens." : "Edit and translate again."}</Muted>
            <Field label="Simplified English" value={edit} onChangeText={setEdit} multiline />
            <Button title="Translate this version" kind="ghost" busy={busy} onPress={() => run(edit, "restricted")} />
          </View>
        </View>
      )}

      {fromRes && (
        <View style={{ marginTop: 20 }}>
          <H2>Translation</H2>
          {(fromRes.natural || fromRes.literal).map((t, i) => <Text selectable key={i} style={{ fontSize: 18, color: colors.ink, marginBottom: 6 }}>{t}</Text>)}
          <Muted>{fromRes.natural ? "Literal reading: " + fromRes.literal.join(" ") : "This is a word-by-word reading. Smoothing it into natural English is optional and uses a few tokens."}</Muted>
          {fromRes.interlinear.map((s, i) => <Interlinear key={i} items={inter(s)} />)}
          <Muted>{fromRes.usage ? `Used ${fmtTokens(tokenCount(fromRes.usage))} tokens` : "No tokens used"}</Muted>
          <Notes issues={fromRes.issues} />
        </View>
      )}
    </View>
  );
}
