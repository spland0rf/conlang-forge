import React, { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from "react-native";
import { ApiError } from "../api";
import { errorText } from "../format";
import { useSession } from "../session";
import type { RegisterResult, Session } from "../types";
import { checkEmail, checkNewPassword } from "../validate";
import { Button, Card, ErrorText, Field, H1, Muted, OkText, Segmented } from "../ui/components";
import { colors } from "../ui/theme";
import { signInWithGoogle } from "../googleNative";

type Mode = "in" | "up" | "check" | "forgot";

export default function AuthScreen() {
  const { api, config, configError, server, changeServer, signIn, reloadConfig } = useSession();
  const [mode, setMode] = useState<Mode>("in");
  const [justCreated, setJustCreated] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [serverEdit, setServerEdit] = useState(false);
  const [serverText, setServerText] = useState(server);

  const wrap = async (fn: () => Promise<void>) => {
    setErr(null); setNote(null); setBusy(true);
    try { await fn(); } catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  };

  const submit = () => wrap(async () => {
    const bad = checkEmail(email) || (mode === "up" ? checkNewPassword(password) : password ? null : "Enter your password.");
    if (bad) { setErr(bad); return; }
    try {
      if (mode === "in") {
        await signIn(await api.post<Session>("/api/auth/login", { email: email.trim(), password }));
      } else {
        const r = await api.post<RegisterResult>("/api/auth/register", { email: email.trim(), password, display_name: name.trim() });
        if ("verification_required" in r) { setJustCreated(true); setMode("check"); }
        else await signIn(r);
      }
    } catch (e) {
      if (e instanceof ApiError && e.code === "email_not_verified") { setJustCreated(false); setMode("check"); return; }
      throw e;
    }
  });

  const google = () => wrap(async () => {
    const sess = await signInWithGoogle(api);
    if (sess) await signIn(sess);
  });
  const resend = () => wrap(async () => { await api.post("/api/auth/resend", { email: email.trim() }); setNote("Sent. It can take a minute to arrive."); });
  const forgot = () => wrap(async () => {
    const bad = checkEmail(email); if (bad) { setErr(bad); return; }
    const r = await api.post<{ message: string }>("/api/auth/forgot", { email: email.trim() }); setNote(r.message);
  });

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 64 }} keyboardShouldPersistTaps="handled">
        <H1>Conlang Forge</H1>
        <Muted style={{ marginBottom: 20 }}>Invent languages for your worlds, then translate to and from them.</Muted>

        {configError && (
          <Card>
            <ErrorText>{configError}</ErrorText>
            <Button title="Try again" kind="ghost" onPress={reloadConfig} />
          </Card>
        )}

        {mode === "check" ? (
          <Card>
            <H1>Check your email</H1>
            <Text style={{ color: colors.ink, fontSize: 16, lineHeight: 23 }}>
              {justCreated ? "Your account is created. We sent a verification link to " : "This account is not confirmed yet. We sent a verification link to "}
              <Text style={{ fontWeight: "700" }}>{email.trim()}</Text>.
            </Text>
            <Text style={{ color: colors.ink, fontSize: 16, lineHeight: 23, marginTop: 10 }}>
              Open the email and click the link to confirm your address.{" "}
              <Text style={{ fontWeight: "700" }}>You won't be able to log in until you have verified your account.</Text>
            </Text>
            <Muted style={{ marginTop: 10 }}>The link works for 48 hours. If you don't see the email, look in your spam or junk folder.</Muted>
            <ErrorText>{err}</ErrorText><OkText>{note}</OkText>
            <View style={{ gap: 10, marginTop: 14 }}>
              <Button title="Login" onPress={() => { setMode("in"); setErr(null); setNote(null); }} />
              <Button title="Send the link again" kind="ghost" busy={busy} onPress={resend} />
            </View>
          </Card>
        ) : mode === "forgot" ? (
          <Card>
            <H1>Reset your password</H1>
            <Muted style={{ marginBottom: 12 }}>Enter your email address and we will send you a link to choose a new password. Open the link in your browser.</Muted>
            <Field label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
            <ErrorText>{err}</ErrorText><OkText>{note}</OkText>
            <View style={{ gap: 10 }}>
              <Button title="Send reset link" busy={busy} onPress={forgot} />
              <Button title="Back to login" kind="ghost" onPress={() => { setMode("in"); setErr(null); setNote(null); }} />
            </View>
          </Card>
        ) : (
          <Card>
            <Segmented value={mode} onChange={(v) => { setMode(v as Mode); setErr(null); }} options={[["in", "Sign in"], ["up", "Create account"]]} />
            {mode === "up" && config && !config.registration_open && <ErrorText>New accounts are closed on this server right now.</ErrorText>}
            {mode === "up" && <Field label="Name (optional)" value={name} onChangeText={setName} autoComplete="name" />}
            <Field label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
            <Field label={mode === "up" ? "Password (at least 10 characters)" : "Password"} value={password} onChangeText={setPassword}
              secureTextEntry autoCapitalize="none" autoComplete={mode === "in" ? "current-password" : "new-password"} onSubmitEditing={submit} />
            <ErrorText>{err}</ErrorText>
            <Button title={mode === "in" ? "Sign in" : "Create account"} busy={busy} onPress={submit} />
            {config?.google_app_enabled && (
              <Button title="Continue with Google" kind="ghost" busy={busy} style={{ marginTop: 10 }} onPress={google} />
            )}
            {mode === "in" && <Button title="Forgot your password?" kind="ghost" style={{ marginTop: 10 }} onPress={() => { setMode("forgot"); setErr(null); }} />}
          </Card>
        )}

        <View style={{ marginTop: 8 }}>
          {!serverEdit ? (
            <Text style={{ color: colors.muted, fontSize: 13 }} onPress={() => setServerEdit(true)}>Server: {server} (change)</Text>
          ) : (
            <Card>
              <Field label="Server address" value={serverText} onChangeText={setServerText} autoCapitalize="none" keyboardType="url" />
              <View style={{ flexDirection: "row", gap: 10 }}>
                <Button title="Use this server" style={{ flex: 1 }} onPress={() => wrap(async () => { await changeServer(serverText); setServerEdit(false); })} />
                <Button title="Cancel" kind="ghost" onPress={() => { setServerText(server); setServerEdit(false); }} />
              </View>
            </Card>
          )}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
