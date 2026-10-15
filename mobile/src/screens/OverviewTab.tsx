import React, { useState } from "react";
import { Alert, Modal, Text, View } from "react-native";
import { errorText } from "../format";
import { useLanguage } from "../language";
import { useSession } from "../session";
import { Button, Card, ErrorText, Field, H2, Muted } from "../ui/components";
import { colors } from "../ui/theme";
import type { TabKey } from "./LanguageScreen";

const list = (a?: string[]) => (a && a.length ? a.join(", ") : "none");
const QUESTIONS: Record<string, string> = { particle: "a question word", "verb inversion": "swapping the verb and subject", intonation: "tone of voice", "verbal affix": "an ending on the verb" };

function Letters({ items, tint }: { items: string[]; tint?: boolean }) {
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, marginVertical: 6 }}>
      {items.map((c, i) => (
        <View key={c + i} style={{ minWidth: 36, paddingVertical: 6, paddingHorizontal: 8, borderRadius: 8, backgroundColor: tint ? "#f1ebfb" : "#f1ebfb", alignItems: "center" }}>
          <Text style={{ fontSize: 18, color: colors.word }}>{c}</Text>
        </View>
      ))}
    </View>
  );
}
const Fact = ({ k, v }: { k: string; v: string }) => (
  <View style={{ flexDirection: "row", paddingVertical: 5, borderBottomWidth: 1, borderBottomColor: colors.line }}>
    <Text style={{ width: 130, color: colors.muted, fontSize: 14 }}>{k}</Text>
    <Text style={{ flex: 1, color: colors.ink, fontSize: 14 }}>{v}</Text>
  </View>
);

export default function OverviewTab({ goTo, onDeleted, onRenamed }: { goTo(t: TabKey): void; onDeleted(): void; onRenamed(): void }) {
  const { api } = useSession();
  const { lang, reload } = useLanguage();
  const p = lang.profile, g = p.grammar, s = p.sounds;
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState(lang.name);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const rename = async () => {
    setBusy(true); setErr(null);
    try { await api.patch(`/api/conlangs/${lang.id}`, { name }); setRenaming(false); onRenamed(); await reload(); }
    catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  };
  const remove = () => Alert.alert(`Delete ${lang.name}?`, "The language and its dictionary will be removed from your account. This cannot be undone.", [
    { text: "Cancel", style: "cancel" },
    { text: "Delete language", style: "destructive", onPress: async () => {
      try { await api.del(`/api/conlangs/${lang.id}`); onDeleted(); } catch (e) { Alert.alert("Could not delete", errorText(e)); }
    } },
  ]);

  return (
    <View>
      <Card>
        <H2>Sounds</H2>
        <Muted>Consonants</Muted><Letters items={s.consonants} />
        <Muted>Vowels</Muted><Letters items={s.vowels} tint />
        <Muted>{`Stress is ${s.stress === "none" ? "even" : "on the " + s.stress + " syllable"}. About ${Math.round(p.one_syllable_share * 100)}% of words have one syllable.`}</Muted>
      </Card>
      <Card>
        <H2>A few words</H2>
        {p.quick_words.map((w) => (
          <View key={w.en} style={{ flexDirection: "row", alignItems: "baseline", paddingVertical: 4 }}>
            <Text style={{ width: 110, color: colors.ink }}>{w.en}</Text>
            <Text selectable style={{ flex: 1, fontSize: 19, color: colors.word, fontWeight: "600" }}>{w.form}</Text>
            <Text style={{ color: colors.muted }}>{w.ipa}</Text>
          </View>
        ))}
      </Card>
      <Card>
        <H2>Grammar at a glance</H2>
        <Fact k="Word building" v={g.type} /><Fact k="Sentence order" v={g.word_order} /><Fact k="Adjectives" v={g.adjectives} />
        <Fact k="Small words" v={g.adposition + "s"} /><Fact k="Number" v={["singular", ...g.number].join(", ")} /><Fact k="Cases" v={list(g.cases)} />
        <Fact k="Genders" v={list(g.genders)} /><Fact k="Articles" v={g.definiteness} /><Fact k="Tenses" v={list(g.tenses)} />
        <Fact k="Verbs agree with" v={g.agreement === "none" ? "nothing" : g.agreement} /><Fact k="Yes/no questions" v={QUESTIONS[g.questions] || g.questions} />
        <Fact k="Counting base" v={String(g.numeral_base)} />
        <Button title="Start the grammar book" style={{ marginTop: 14 }} onPress={() => goTo("book")} />
      </Card>
      <View style={{ flexDirection: "row", gap: 10 }}>
        <Button title="Rename" kind="ghost" style={{ flex: 1 }} onPress={() => { setName(lang.name); setErr(null); setRenaming(true); }} />
        <Button title="Delete" kind="ghost" style={{ flex: 1, borderColor: colors.error }} onPress={remove} />
      </View>

      <Modal visible={renaming} transparent animationType="fade" onRequestClose={() => setRenaming(false)}>
        <View style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.4)", justifyContent: "center", padding: 24 }}>
          <Card>
            <H2>Rename language</H2>
            <Field label="Name" value={name} onChangeText={setName} maxLength={80} autoFocus />
            <ErrorText>{err}</ErrorText>
            <View style={{ flexDirection: "row", gap: 10 }}>
              <Button title="Cancel" kind="ghost" style={{ flex: 1 }} onPress={() => setRenaming(false)} />
              <Button title="Rename" busy={busy} style={{ flex: 1 }} onPress={rename} />
            </View>
          </Card>
        </View>
      </Modal>
    </View>
  );
}
