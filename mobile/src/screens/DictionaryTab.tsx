import React, { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, SectionList, Text, TextInput, View } from "react-native";
import { buildIndex, details, search, type Direction } from "../dictionary";
import { errorText } from "../format";
import { useLanguage } from "../language";
import { useSession } from "../session";
import type { DictEntry } from "../types";
import { Button, ErrorText, Muted, Segmented } from "../ui/components";
import { colors } from "../ui/theme";

const cache = new Map<string, DictEntry[]>();

export default function DictionaryTab() {
  const { api } = useSession();
  const { lang, script, query } = useLanguage();
  const [entries, setEntries] = useState<DictEntry[] | null>(cache.get(lang.id + lang.updated_at + script) ?? null);
  const [err, setErr] = useState<string | null>(null);
  const [dir, setDir] = useState<Direction>("en");
  const [q, setQ] = useState("");
  const [pos, setPos] = useState("");
  const list = useRef<SectionList<any>>(null);

  const load = async () => {
    setErr(null);
    try {
      const key = lang.id + lang.updated_at + script;
      const d = await api.get<{ entries: DictEntry[] }>(`/api/conlangs/${lang.id}/dictionary.json${query}`);
      cache.set(key, d.entries); setEntries(d.entries);
    } catch (e) { setErr(errorText(e)); }
  };
  useEffect(() => { if (!entries) load(); }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  const index = useMemo(() => (entries ? buildIndex(entries, lang.profile.sounds) : null), [entries, lang.profile.sounds]);
  const result = useMemo(() => (index ? search(index, { dir, q, pos }) : null), [index, dir, q, pos]);

  if (err) return <View><ErrorText>{err}</ErrorText><Button title="Try again" kind="ghost" onPress={load} /></View>;
  if (!index || !result) return <ActivityIndicator color={colors.accent} style={{ marginTop: 20 }} />;

  const sections = result.sections.filter((s) => s.data.length);
  const jumpLetters = q ? [] : sections.map((s) => s.title);
  return (
    <View style={{ flex: 1 }}>
      <TextInput value={q} onChangeText={setQ} placeholder="Search words or meanings" placeholderTextColor={colors.muted} accessibilityLabel="Search the dictionary"
        autoCapitalize="none" autoCorrect={false} clearButtonMode="while-editing"
        style={{ borderWidth: 1, borderColor: colors.line, borderRadius: 10, backgroundColor: colors.card, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16, color: colors.ink }} />
      <View style={{ height: 10 }} />
      <Segmented value={dir} onChange={(v) => setDir(v as Direction)} options={[["en", `English → ${lang.name}`], ["con", `${lang.name} → English`]]} />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0, marginBottom: 6 }}>
        {["", ...index.posOptions].map((p) => (
          <Pressable key={p || "all"} accessibilityRole="button" accessibilityState={{ selected: pos === p }} onPress={() => setPos(p)}
            style={{ paddingVertical: 6, paddingHorizontal: 12, borderRadius: 16, marginRight: 6, backgroundColor: pos === p ? colors.accent : "#e6f0ec" }}>
            <Text style={{ color: pos === p ? colors.accentInk : colors.accent, fontSize: 13 }}>{p || "All types"}</Text>
          </Pressable>
        ))}
      </ScrollView>
      {jumpLetters.length > 1 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0, marginBottom: 4 }}>
          {jumpLetters.map((l, i) => (
            <Text key={l} accessibilityRole="button" onPress={() => list.current?.scrollToLocation({ sectionIndex: i, itemIndex: 0, viewPosition: 0, animated: true })}
              style={{ paddingHorizontal: 9, paddingVertical: 4, color: colors.word, fontSize: 16, fontWeight: "600" }}>{l}</Text>
          ))}
        </ScrollView>
      )}
      <Muted>{result.hits.length ? `${result.hits.length.toLocaleString()} ${result.hits.length === 1 ? "entry" : "entries"}` : ""}</Muted>
      <SectionList
        ref={list} sections={sections} keyExtractor={(e, i) => e.form + e.en + i} stickySectionHeadersEnabled
        keyboardShouldPersistTaps="handled" initialNumToRender={30} windowSize={9}
        onScrollToIndexFailed={() => {}}
        ListEmptyComponent={<Muted>No entries match. Try fewer letters, or search by the English meaning.</Muted>}
        renderSectionHeader={({ section }) => section.title ? (
          <View style={{ backgroundColor: colors.bg, paddingVertical: 4 }}>
            <Text style={{ fontSize: 20, fontWeight: "700", color: colors.word }}>{section.title}</Text>
          </View>) : null}
        renderItem={({ item: e }) => {
          const more = details(e);
          const first = dir === "en" ? e.en : e.form, second = dir === "en" ? e.form : e.en;
          return (
            <View style={{ paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.line }}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" }}>
                <Text selectable style={{ fontSize: 17, fontWeight: "600", color: dir === "en" ? colors.ink : colors.word, flexShrink: 1 }}>{first}</Text>
                <Text selectable style={{ fontSize: 17, color: dir === "en" ? colors.word : colors.ink, marginLeft: 12, flexShrink: 1, textAlign: "right" }}>{second}</Text>
              </View>
              <Text style={{ color: colors.muted, fontSize: 12 }}>{`${e.pos}${e.ipa ? "  ·  " + e.ipa : ""}`}</Text>
              {more ? <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }}>{more}</Text> : null}
            </View>
          );
        }}
      />
    </View>
  );
}
