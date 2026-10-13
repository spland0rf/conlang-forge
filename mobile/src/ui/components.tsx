import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle } from "react-native";
import { colors, space } from "./theme";

export function Button({ title, onPress, kind = "primary", disabled, busy, style }: {
  title: string; onPress: () => void; kind?: "primary" | "ghost"; disabled?: boolean; busy?: boolean; style?: ViewStyle;
}) {
  const off = disabled || busy;
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={title} onPress={off ? undefined : onPress}
      style={({ pressed }) => [s.btn, kind === "primary" ? s.btnPrimary : s.btnGhost, off && { opacity: 0.5 }, pressed && { opacity: 0.8 }, style]}>
      {busy ? <ActivityIndicator color={kind === "primary" ? colors.accentInk : colors.accent} />
        : <Text style={[s.btnText, kind === "ghost" && { color: colors.accent }]}>{title}</Text>}
    </Pressable>
  );
}

export function Field({ label, ...rest }: { label: string } & TextInputProps) {
  return (
    <View style={{ marginBottom: space.md }}>
      <Text style={s.label}>{label}</Text>
      <TextInput accessibilityLabel={label} placeholderTextColor={colors.muted} style={[s.input, rest.multiline && { minHeight: 110, textAlignVertical: "top" }]} {...rest} />
    </View>
  );
}

export function Card({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[s.card, style]}>{children}</View>;
}
export const ErrorText = ({ children }: { children?: React.ReactNode }) => (children ? <Text accessibilityRole="alert" style={s.error}>{children}</Text> : null);
export const OkText = ({ children }: { children?: React.ReactNode }) => (children ? <Text style={s.ok}>{children}</Text> : null);
export const Muted = ({ children, style }: { children?: React.ReactNode; style?: any }) => <Text style={[s.muted, style]}>{children}</Text>;
export const H1 = ({ children }: { children?: React.ReactNode }) => <Text accessibilityRole="header" style={s.h1}>{children}</Text>;
export const H2 = ({ children }: { children?: React.ReactNode }) => <Text accessibilityRole="header" style={s.h2}>{children}</Text>;

export function Segmented({ options, value, onChange }: { options: [string, string][]; value: string; onChange: (v: string) => void }) {
  return (
    <View style={s.seg} accessibilityRole="tablist">
      {options.map(([v, label]) => (
        <Pressable key={v} accessibilityRole="tab" accessibilityState={{ selected: value === v }} onPress={() => onChange(v)}
          style={[s.segItem, value === v && s.segOn]}>
          <Text style={[s.segText, value === v && { color: colors.accentInk }]} numberOfLines={1}>{label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export function Check({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: value }} onPress={() => onChange(!value)} style={s.check}>
      <View style={[s.box, value && { backgroundColor: colors.accent }]}>{value && <Text style={{ color: "#fff", fontSize: 14 }}>✓</Text>}</View>
      <Text style={[s.muted, { flex: 1 }]}>{label}</Text>
    </Pressable>
  );
}

const s = StyleSheet.create({
  btn: { minHeight: 48, borderRadius: 10, paddingHorizontal: space.lg, alignItems: "center", justifyContent: "center" },
  btnPrimary: { backgroundColor: colors.accent },
  btnGhost: { borderWidth: 1, borderColor: colors.accent },
  btnText: { color: colors.accentInk, fontSize: 16, fontWeight: "600" },
  label: { color: colors.muted, fontSize: 13, marginBottom: 4 },
  input: { borderWidth: 1, borderColor: colors.line, borderRadius: 10, backgroundColor: colors.card, color: colors.ink, fontSize: 16, paddingHorizontal: space.md, paddingVertical: 10, minHeight: 46 },
  card: { backgroundColor: colors.card, borderRadius: 12, borderWidth: 1, borderColor: colors.line, padding: space.lg, marginBottom: space.md },
  error: { color: colors.error, marginVertical: space.sm, fontSize: 15 },
  ok: { color: colors.ok, marginVertical: space.sm, fontSize: 15 },
  muted: { color: colors.muted, fontSize: 14, lineHeight: 20 },
  h1: { color: colors.ink, fontSize: 26, fontWeight: "700", marginBottom: space.sm },
  h2: { color: colors.ink, fontSize: 18, fontWeight: "600", marginBottom: space.sm },
  seg: { flexDirection: "row", borderWidth: 1, borderColor: colors.accent, borderRadius: 10, overflow: "hidden", marginBottom: space.md },
  segItem: { flex: 1, paddingVertical: 10, paddingHorizontal: 6, alignItems: "center" },
  segOn: { backgroundColor: colors.accent },
  segText: { color: colors.accent, fontWeight: "600", fontSize: 14 },
  check: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 8 },
  box: { width: 22, height: 22, borderRadius: 5, borderWidth: 1, borderColor: colors.accent, alignItems: "center", justifyContent: "center" },
});
