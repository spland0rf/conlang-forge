import React from "react";
import { ScrollView, Text, View, KeyboardAvoidingView, Platform } from "react-native";
import type { LanguageSummary } from "../types";
import { H1, Muted } from "../ui/components";
import { colors } from "../ui/theme";
import TranslateTab from "./TranslateTab";

export default function LanguageScreen({ lang, onBack }: { lang: LanguageSummary; onBack: () => void }) {
  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 56 }} keyboardShouldPersistTaps="handled">
        <Text accessibilityRole="button" onPress={onBack} style={{ color: colors.accent, fontSize: 16, marginBottom: 10 }}>‹ Languages</Text>
        <H1>{lang.name}</H1>
        <Muted style={{ marginBottom: 14 }}>Translate</Muted>
        <TranslateTab lang={lang} />
        <View style={{ height: 40 }} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
