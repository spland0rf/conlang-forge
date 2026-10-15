import { StatusBar } from "expo-status-bar";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, BackHandler, Platform, Pressable, StatusBar as RNStatusBar, Text, View } from "react-native";
import { SessionProvider, useSession } from "./src/session";
import type { LanguageSummary } from "./src/types";
import { colors } from "./src/ui/theme";
import AuthScreen from "./src/screens/AuthScreen";
import LanguageScreen from "./src/screens/LanguageScreen";
import LanguagesScreen from "./src/screens/LanguagesScreen";
import { ForgeScreen, SampleScreen } from "./src/screens/CreateScreens";
import ScriptEditor from "./src/screens/ScriptEditor";
import ScriptsScreen from "./src/screens/ScriptsScreen";

type Top = "languages" | "writing" | "forge" | "sample";
const TOPS: [Top, string][] = [["languages", "Languages"], ["writing", "Writing"], ["forge", "Forge"], ["sample", "From a sample"]];

function Root() {
  const { me, ready } = useSession();
  const [lang, setLang] = useState<LanguageSummary | null>(null);
  const [top, setTop] = useState<Top>("languages");
  const [refreshKey, setRefreshKey] = useState(0);        // bump to make the languages list reload
  const [scriptsKey, setScriptsKey] = useState(0);         // bump to make the writing systems list reload
  const [editing, setEditing] = useState<{ id: string | null; lang?: string } | null>(null);      // the writing-system editor

  useEffect(() => {          // Android back button goes up one level
    const sub = BackHandler.addEventListener("hardwareBackPress", () => { if (editing) { setEditing(null); return true; } if (lang) { setLang(null); return true; } if (top !== "languages") { setTop("languages"); return true; } return false; });
    return () => sub.remove();
  }, [lang, top, editing]);
  useEffect(() => { if (!me) { setLang(null); setEditing(null); } }, [me]);

  if (!ready) return <View style={{ flex: 1, justifyContent: "center", backgroundColor: colors.bg }}><ActivityIndicator color={colors.accent} /></View>;
  if (!me) return <AuthScreen />;
  const created = (l: LanguageSummary) => { setRefreshKey((k) => k + 1); setTop("languages"); setLang(l); };
  const show = (t: Top) => ({ flex: 1, display: top === t ? "flex" : "none" } as const);
  const topPad = Platform.OS === "android" ? (RNStatusBar.currentHeight ?? 24) : 54;      // clear the clock and notch
  const main = lang ? (
    <LanguageScreen key={lang.id} summary={lang} onBack={() => setLang(null)} onChanged={() => setRefreshKey((k) => k + 1)} onOpen={setLang}
      onEditScript={(id, languageId) => setEditing({ id, lang: languageId })} scriptsKey={scriptsKey} />
  ) : (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <View style={{ paddingTop: topPad, flexDirection: "row", borderBottomWidth: 1, borderBottomColor: colors.line, backgroundColor: colors.card }} accessibilityRole="tablist">
        {TOPS.map(([k, label]) => (
          <Pressable key={k} accessibilityRole="tab" accessibilityState={{ selected: top === k }} onPress={() => setTop(k)}
            style={{ flex: 1, alignItems: "center", paddingVertical: 14, borderBottomWidth: 3, borderBottomColor: top === k ? colors.accent : "transparent" }}>
            <Text numberOfLines={1} style={{ fontSize: 13, fontWeight: top === k ? "700" : "500", color: top === k ? colors.accent : colors.muted }}>{label}</Text>
          </Pressable>
        ))}
      </View>
      {/* all four stay mounted so a half-typed sample survives a trip to another tab */}
      <View style={show("languages")}><LanguagesScreen onOpen={setLang} refreshKey={refreshKey} onForge={() => setTop("forge")} /></View>
      <View style={show("writing")}><ScriptsScreen refreshKey={scriptsKey} onOpen={(id) => setEditing({ id })} onNew={() => setEditing({ id: null })} /></View>
      <View style={show("forge")}><ForgeScreen onCreated={created} /></View>
      <View style={show("sample")}><SampleScreen onCreated={created} /></View>
    </View>
  );
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <View style={{ flex: 1, display: editing ? "none" : "flex" }}>{main}</View>
      {editing ? (
        <View style={{ flex: 1 }}>
          <ScriptEditor key={editing.id ?? "new"} id={editing.id} presetLanguage={editing.lang} onBack={() => setEditing(null)}
            onChanged={() => setScriptsKey((k) => k + 1)} onOpenScript={(id) => setEditing({ id })}
            onOpenLanguage={(l) => { setEditing(null); setRefreshKey((k) => k + 1); setLang(l); }} />
        </View>
      ) : null}
    </View>
  );
}

export default function App() {
  return (
    <SessionProvider>
      <StatusBar style="dark" />
      <Root />
    </SessionProvider>
  );
}
