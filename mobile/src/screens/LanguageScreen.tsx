import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { errorText } from "../format";
import { LanguageProvider, scriptQuery } from "../language";
import { useSession } from "../session";
import type { Language, LanguageSummary, Script } from "../types";
import { Button, ErrorText, H1, Muted, Segmented } from "../ui/components";
import { colors } from "../ui/theme";
import BookTab from "./BookTab";
import DictionaryTab from "./DictionaryTab";
import DownloadsTab from "./DownloadsTab";
import OverviewTab from "./OverviewTab";
import SettingsTab from "./SettingsTab";
import TranslateTab from "./TranslateTab";

export type TabKey = "overview" | "translate" | "settings" | "dictionary" | "book" | "files";
const TABS: [TabKey, string][] = [["overview", "Overview"], ["translate", "Translate"], ["settings", "Settings"], ["dictionary", "Dictionary"], ["book", "Grammar book"], ["files", "Downloads"]];
// Dictionary and book are long lists that scroll themselves; the others scroll with the page.
const SELF_SCROLLING: TabKey[] = ["dictionary", "book"];

export default function LanguageScreen({ summary, onBack, onChanged, onOpen }: {
  summary: LanguageSummary; onBack: () => void; onChanged: () => void; onOpen: (l: LanguageSummary) => void;
}) {
  const { api } = useSession();
  const [lang, setLang] = useState<Language | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<TabKey>("overview");
  const [script, setScript] = useState<Script>("plain");

  const load = useCallback(async () => {
    setErr(null);
    try { setLang(await api.get<Language>(`/api/conlangs/${summary.id}${scriptQuery(script)}`)); }
    catch (e) { setErr(errorText(e)); }
  }, [api, summary.id, script]);
  useEffect(() => { load(); }, [load]);

  const header = (
    <View style={{ paddingHorizontal: 20, paddingTop: 56 }}>
      <Text accessibilityRole="button" onPress={onBack} style={{ color: colors.accent, fontSize: 16, marginBottom: 6 }}>‹ Languages</Text>
      <H1>{lang?.name ?? summary.name}</H1>
      {lang && <Muted>{`${lang.profile.words.toLocaleString()} words · ${lang.profile.grammar.word_order} · ${lang.profile.grammar.type} · seed ${lang.profile.seed}`}</Muted>}
      <View style={{ marginTop: 10 }}>
        <Segmented value={script} onChange={(v) => setScript(v as Script)} options={[["plain", "Plain letters"], ["special", "Special letters"]]} />
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 8 }} accessibilityRole="tablist">
        {TABS.map(([k, label]) => (
          <Pressable key={k} accessibilityRole="tab" accessibilityState={{ selected: tab === k }} onPress={() => setTab(k)}
            style={{ paddingVertical: 10, paddingHorizontal: 14, borderBottomWidth: 3, borderBottomColor: tab === k ? colors.accent : "transparent" }}>
            <Text style={{ fontSize: 15, fontWeight: tab === k ? "700" : "500", color: tab === k ? colors.accent : colors.muted }}>{label}</Text>
          </Pressable>
        ))}
      </ScrollView>
    </View>
  );

  if (!lang) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg }}>
        {header}
        <View style={{ padding: 20 }}>
          {err ? (<><ErrorText>{err}</ErrorText><Button title="Try again" kind="ghost" onPress={load} /></>) : <ActivityIndicator color={colors.accent} />}
        </View>
      </View>
    );
  }

  const ctx = { lang, script, setScript, reload: load, query: scriptQuery(script) };
  const body = (
    tab === "overview" ? <OverviewTab goTo={setTab} onDeleted={() => { onChanged(); onBack(); }} onRenamed={onChanged} />
    : tab === "translate" ? <TranslateTab lang={lang} />
    : tab === "settings" ? <SettingsTab onOpenLanguage={(l) => { onChanged(); onOpen(l); }} />
    : tab === "dictionary" ? <DictionaryTab />
    : tab === "book" ? <BookTab />
    : <DownloadsTab />
  );
  return (
    <LanguageProvider value={ctx}>
      <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        {SELF_SCROLLING.includes(tab) ? (
          <View style={{ flex: 1 }}>{header}<View style={{ flex: 1, paddingHorizontal: 20 }}>{body}</View></View>
        ) : (
          <ScrollView contentContainerStyle={{ paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
            {header}<View style={{ paddingHorizontal: 20 }}>{body}</View>
          </ScrollView>
        )}
      </KeyboardAvoidingView>
    </LanguageProvider>
  );
}
