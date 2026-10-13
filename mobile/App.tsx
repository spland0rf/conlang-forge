import { StatusBar } from "expo-status-bar";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, BackHandler, View } from "react-native";
import { SessionProvider, useSession } from "./src/session";
import type { LanguageSummary } from "./src/types";
import { colors } from "./src/ui/theme";
import AuthScreen from "./src/screens/AuthScreen";
import LanguageScreen from "./src/screens/LanguageScreen";
import LanguagesScreen from "./src/screens/LanguagesScreen";

function Root() {
  const { me, ready } = useSession();
  const [lang, setLang] = useState<LanguageSummary | null>(null);

  useEffect(() => {          // Android back button goes up one level
    const sub = BackHandler.addEventListener("hardwareBackPress", () => { if (lang) { setLang(null); return true; } return false; });
    return () => sub.remove();
  }, [lang]);
  useEffect(() => { if (!me) setLang(null); }, [me]);

  if (!ready) return <View style={{ flex: 1, justifyContent: "center", backgroundColor: colors.bg }}><ActivityIndicator color={colors.accent} /></View>;
  if (!me) return <AuthScreen />;
  return lang ? <LanguageScreen lang={lang} onBack={() => setLang(null)} /> : <LanguagesScreen onOpen={setLang} />;
}

export default function App() {
  return (
    <SessionProvider>
      <StatusBar style="dark" />
      <Root />
    </SessionProvider>
  );
}
