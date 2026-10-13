import React from "react";
import { ActivityIndicator, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle } from "react-native";
import { colors, space } from "./theme";

export function Button({ title, onPress, kind = "primary", disabled, busy, style }: {
  title: string; onPress: () => void; kind?: "primary" | "ghost"; disabled?: boolean; busy?: boolean; style?: ViewStyle;
}) {
  const off = disabled || busy;
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={title} onPress={off ? undefined : onPress}
      style={({ pressed }: { pressed: boolean }) => [s.btn, kind === "primary" ? s.btnPrimary : s.btnGhost, off && { opacity: 0.5 }, pressed && { opacity: 0.8 }, style]}>
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
  select: { flexDirection: "row", alignItems: "center", borderWidth: 1, borderColor: colors.line, borderRadius: 10, backgroundColor: colors.card, paddingHorizontal: space.md, minHeight: 46 },
  stepBtn: { width: 44, height: 44, borderRadius: 10, borderWidth: 1, borderColor: colors.accent, alignItems: "center", justifyContent: "center" },
  stepTxt: { color: colors.accent, fontSize: 22, fontWeight: "600" },
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

/** A pick-one control: shows the current choice and opens a list. */
export function Select({ label, options, value, onChange }: { label: string; options: { value: any; label: string }[]; value: any; onChange: (v: any) => void }) {
  const [open, setOpen] = React.useState(false);
  const cur = options.find((o) => JSON.stringify(o.value) === JSON.stringify(value));
  return (
    <View>
      <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={() => setOpen(true)} style={s.select}>
        <Text style={{ color: colors.ink, fontSize: 16, flex: 1 }}>{cur ? cur.label : String(value)}</Text>
        <Text style={{ color: colors.muted }}>▾</Text>
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.4)", justifyContent: "center", padding: 20 }} onPress={() => setOpen(false)}>
          <View style={{ backgroundColor: colors.card, borderRadius: 12, maxHeight: "80%", padding: 8 }}>
            <Text style={{ fontWeight: "700", fontSize: 16, color: colors.ink, padding: 10 }}>{label}</Text>
            <ScrollView>
              {options.map((o, i) => {
                const on = JSON.stringify(o.value) === JSON.stringify(value);
                return (
                  <Pressable key={i} accessibilityRole="button" accessibilityState={{ selected: on }} onPress={() => { setOpen(false); onChange(o.value); }}
                    style={{ padding: 12, borderRadius: 8, backgroundColor: on ? "#e6f0ec" : "transparent" }}>
                    <Text style={{ fontSize: 16, color: on ? colors.accent : colors.ink, fontWeight: on ? "700" : "400" }}>{o.label}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          </View>
        </Pressable>
      </Modal>
    </View>
  );
}

/** A number with minus and plus buttons. Typing a number also works; the value is applied when you finish. */
export function Stepper({ value, min, max, step = 1, onChange, suffix }: { value: number; min: number; max: number; step?: number; onChange: (v: number) => void; suffix?: string }) {
  const [text, setText] = React.useState(String(value));
  React.useEffect(() => { setText(String(value)); }, [value]);
  const clamp = (x: number) => Math.min(max, Math.max(min, x));
  const round = (x: number) => Math.round(x * 1e6) / 1e6;
  const commit = (x: number) => { if (!Number.isNaN(x)) onChange(round(clamp(x))); else setText(String(value)); };
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
      <Pressable accessibilityRole="button" accessibilityLabel="decrease" onPress={() => commit(value - step)} style={s.stepBtn}><Text style={s.stepTxt}>−</Text></Pressable>
      <TextInput value={text} onChangeText={setText} onEndEditing={() => commit(parseFloat(text))} onSubmitEditing={() => commit(parseFloat(text))}
        keyboardType="decimal-pad" style={[s.input, { width: 80, textAlign: "center" }]} accessibilityLabel="value" />
      <Pressable accessibilityRole="button" accessibilityLabel="increase" onPress={() => commit(value + step)} style={s.stepBtn}><Text style={s.stepTxt}>+</Text></Pressable>
      {suffix ? <Text style={{ color: colors.muted }}>{suffix}</Text> : null}
    </View>
  );
}

/** Toggle chips for choosing several things. */
export function Chips({ options, selected, locked = [], onToggle }: { options: { value: string; label: string; hint?: string; group?: string }[]; selected: string[]; locked?: string[]; onToggle: (value: string, on: boolean) => void }) {
  const groups = [...new Set(options.map((o) => o.group || ""))];
  return (
    <View>
      {groups.map((g) => (
        <View key={g} style={{ marginBottom: 6 }}>
          {g ? <Text style={{ color: colors.muted, fontSize: 12, marginBottom: 2 }}>{g}</Text> : null}
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
            {options.filter((o) => (o.group || "") === g).map((o) => {
              const on = selected.includes(o.value), lock = locked.includes(o.value);
              return (
                <Pressable key={o.value} accessibilityRole="checkbox" accessibilityState={{ checked: on, disabled: lock }} accessibilityLabel={o.hint || o.label}
                  onPress={lock ? undefined : () => onToggle(o.value, !on)}
                  style={{ minWidth: 40, paddingVertical: 7, paddingHorizontal: 11, borderRadius: 16, borderWidth: 1, borderColor: colors.accent, backgroundColor: on ? colors.accent : "transparent", opacity: lock ? 0.7 : 1 }}>
                  <Text style={{ fontSize: 15, color: on ? colors.accentInk : colors.accent }}>{o.label}</Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      ))}
    </View>
  );
}
