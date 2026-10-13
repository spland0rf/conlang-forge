import React, { useState } from "react";
import { Modal, Text, View } from "react-native";
import { errorText } from "../format";
import { useSession } from "../session";
import { Button, ErrorText, Field, H1, Muted } from "../ui/components";
import { colors } from "../ui/theme";

// "Delete account" link plus a confirmation sheet. Google Play requires apps with sign-up to offer this.
export default function DeleteAccount() {
  const { api, me, signOut } = useSession();
  const [open, setOpen] = useState(false);
  const [secret, setSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const hasPassword = (me as any)?.password_set !== 0 && (me as any)?.password_set !== false;

  async function go() {
    setBusy(true); setErr(null);
    try {
      await api.post("/api/me/delete", hasPassword ? { password: secret } : { confirm_email: secret });
      setOpen(false);
      await signOut();
    } catch (e) { setErr(errorText(e)); }
    setBusy(false);
  }

  return (
    <>
      <Text accessibilityRole="button" onPress={() => { setSecret(""); setErr(null); setOpen(true); }}
        style={{ color: colors.muted, fontSize: 13, paddingHorizontal: 20, marginBottom: 8, textDecorationLine: "underline" }}>Delete account</Text>
      <Modal visible={open} animationType="slide" onRequestClose={() => setOpen(false)}>
        <View style={{ flex: 1, backgroundColor: colors.bg, padding: 20, paddingTop: 60 }}>
          <H1>Delete your account?</H1>
          <Muted style={{ marginBottom: 16 }}>
            This permanently deletes your account and every language saved under it. It cannot be undone.
          </Muted>
          <Field label={hasPassword ? "Your password" : "Type your email address to confirm"} value={secret} onChangeText={setSecret}
            secureTextEntry={hasPassword} autoCapitalize="none" autoCorrect={false} />
          <ErrorText>{err}</ErrorText>
          <Button title="Delete my account" busy={busy} disabled={!secret} onPress={go} />
          <Button title="Keep my account" kind="ghost" style={{ marginTop: 10 }} onPress={() => setOpen(false)} />
        </View>
      </Modal>
    </>
  );
}
