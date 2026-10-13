import { StatusBar } from "expo-status-bar";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, BackHandler, Pressable, Text, View } from "react-native";
import { SessionProvider, useSession } from "./src/session";
import type { LanguageSummary } from "./src/types";
import { colors } from "./src/ui/theme";
import AuthScreen from "./src/screens/AuthScreen";
import LanguageScreen from "./src/screens/LanguageScreen";
import LanguagesScreen from "./src/screens/LanguagesScreen";
import { ForgeScreen, SampleScreen } from "./src/screens/CreateScreens";

type Top = "languages" | "forge" | "sample";
const TOPS: [Top, string][] = [["languages", "Languages"], ["forge", "Forge"], ["sample", "From a sample"]];

function Root() {
  const { me, ready } = useSession();
  const [lang, setLang] = useState<LanguageSummary | null>(null);
  const [top, setTop] = useState<Top>("languages");
  const [refreshKey, setRefreshKey] = useState(0);        // bump to make the languages list reload

  useEffect(() => {          // Android back button goes up one level
    const sub = BackHandler.addEventListener("hardwareBackPress", () => { if (lang) { setLang(null); return true; } if (top !== "languages") { setTop("languages"); return true; } return false; });
    return () => sub.remove();
  }, [lang, top]);
  useEffect(() => { if (!me) setLang(null); }, [me]);

  if (!ready) return <View style={{ flex: 1, justifyContent: "center", backgroundColor: colors.bg }}><ActivityIndicator color={colors.accent} /></View>;
  if (!me) return <AuthScreen />;
  if (lang) return <LanguageScreen key={lang.id} summary={lang} onBack={() => setLang(null)} onChanged={() => setRefreshKey((k) => k + 1)} onOpen={setLang} />;
  const created = (l: LanguageSummary) => { setRefreshKey((k) => k + 1); setTop("languages"); setLang(l); };
  // all three stay mounted so a half-typed sample survives a trip to another tab
  const show = (t: Top) => ({ flex: 1, display: top === t ? "flex" : "none" } as const);
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <View style={show("languages")}><LanguagesScreen onOpen={setLang} refreshKey={refreshKey} onForge={() => setTop("forge")} /></View>
      <View style={show("forge")}><ForgeScreen onCreated={created} /></View>
      <View style={show("sample")}><SampleScreen onCreated={created} /></View>
      <View style={{ flexDirection: "row", borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: colors.card }} accessibilityRole="tablist">
        {TOPS.map(([k, label]) => (
          <Pressable key={k} accessibilityRole="tab" accessibilityState={{ selected: top === k }} onPress={() => setTop(k)}
            style={{ flex: 1, alignItems: "center", paddingVertical: 14, borderTopWidth: 3, borderTopColor: top === k ? colors.accent : "transparent" }}>
            <Text style={{ fontSize: 14, fontWeight: top === k ? "700" : "500", color: top === k ? colors.accent : colors.muted }}>{label}</Text>
          </Pressable>
        ))}
      </View>
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
