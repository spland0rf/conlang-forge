import React, { useState } from "react";
import { Text, View } from "react-native";
import { errorText } from "../format";
import { useLanguage } from "../language";
import { useSession } from "../session";
import { safeName, shareTextFile } from "../share";
import { Button, Card, ErrorText, H2, Muted } from "../ui/components";
import { colors } from "../ui/theme";

export default function DownloadsTab() {
  const { api } = useSession();
  const { lang, query } = useLanguage();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const safe = safeName(lang.name);
  const files = [
    { id: "dict-md", title: "Dictionary (Markdown)", desc: "Both directions, with grammar notes. Opens in any text editor.", path: `dictionary.md`, name: `${safe}_dictionary.md`, mime: "text/markdown" },
    { id: "dict-csv", title: "Dictionary (spreadsheet)", desc: "One row per word, for Excel or Google Sheets.", path: `dictionary.csv`, name: `${safe}_dictionary.csv`, mime: "text/csv" },
    { id: "book", title: "Grammar book (Markdown)", desc: "The full beginner's course.", path: `grammar-book.md`, name: `${safe}_grammar_book.md`, mime: "text/markdown" },
  ];
  const go = async (f: (typeof files)[number]) => {
    setErr(null); setBusy(f.id);
    try { await shareTextFile(f.name, await api.text(`/api/conlangs/${lang.id}/${f.path}${query}`), f.mime); }
    catch (e) { setErr(errorText(e)); } finally { setBusy(null); }
  };
  return (
    <View>
      <H2>Downloads</H2>
      <Muted style={{ marginBottom: 10 }}>Choose where to send each file: Files, Google Drive, email, and so on.</Muted>
      <ErrorText>{err}</ErrorText>
      {files.map((f) => (
        <Card key={f.id}>
          <Text style={{ fontSize: 16, fontWeight: "700", color: colors.ink }}>{f.title}</Text>
          <Muted style={{ marginBottom: 10 }}>{f.desc}</Muted>
          <Button title="Share or save" kind="ghost" busy={busy === f.id} onPress={() => go(f)} />
        </Card>
      ))}
      <Muted>PDF versions are planned.</Muted>
    </View>
  );
}
