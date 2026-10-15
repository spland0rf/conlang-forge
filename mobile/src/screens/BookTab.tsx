import React, { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, FlatList, Linking, Modal, Pressable, ScrollView, Text, View } from "react-native";
import { errorText } from "../format";
import { useLanguage } from "../language";
import { parseMarkdown, type Block, type Span } from "../markdown";
import { useSession } from "../session";
import { Button, ErrorText } from "../ui/components";
import { colors } from "../ui/theme";

const cache = new Map<string, string>();

function Spans({ spans, style }: { spans: Span[]; style?: any }) {
  return (
    <Text style={[{ color: colors.ink, fontSize: 16, lineHeight: 24 }, style]}>
      {spans.map((s, i) => (
        <Text key={i} onPress={s.href && s.href.startsWith("http") ? () => Linking.openURL(s.href!) : undefined}
          style={[s.bold && { fontWeight: "700" }, s.italic && { fontStyle: "italic" }, s.code && { fontFamily: "monospace", backgroundColor: "#f1ebfb", color: colors.word }, s.href && { color: colors.accent, textDecorationLine: "underline" }]}>
          {s.text}
        </Text>
      ))}
    </Text>
  );
}

function BlockView({ b }: { b: Block }) {
  switch (b.kind) {
    case "heading": {
      const size = [0, 26, 22, 18, 16][b.level] || 16;
      return <Text accessibilityRole="header" style={{ fontSize: size, fontWeight: "700", color: colors.ink, marginTop: b.level <= 2 ? 22 : 14, marginBottom: 6 }}>{b.text}</Text>;
    }
    case "paragraph": return <View style={{ marginVertical: 5 }}><Spans spans={b.spans} /></View>;
    case "list": return (
      <View style={{ marginVertical: 5 }}>
        {b.items.map((it, i) => (
          <View key={i} style={{ flexDirection: "row", marginVertical: 2 }}>
            <Text style={{ width: 24, color: colors.muted, fontSize: 16 }}>{b.ordered ? `${i + 1}.` : "•"}</Text>
            <View style={{ flex: 1 }}><Spans spans={it} /></View>
          </View>
        ))}
      </View>);
    case "table": return (
      <ScrollView horizontal style={{ marginVertical: 8 }}>
        <View style={{ borderWidth: 1, borderColor: colors.line, borderRadius: 6 }}>
          {b.head && <View style={{ flexDirection: "row", backgroundColor: "#f1ebfb" }}>{b.head.map((c, i) => <View key={i} style={{ minWidth: 96, maxWidth: 220, padding: 6 }}><Spans spans={c.map((s) => ({ ...s, bold: true }))} style={{ fontSize: 14, lineHeight: 20 }} /></View>)}</View>}
          {b.rows.map((r, ri) => (
            <View key={ri} style={{ flexDirection: "row", borderTopWidth: 1, borderTopColor: colors.line }}>
              {r.map((c, i) => <View key={i} style={{ minWidth: 96, maxWidth: 220, padding: 6 }}><Spans spans={c} style={{ fontSize: 14, lineHeight: 20 }} /></View>)}
            </View>
          ))}
        </View>
      </ScrollView>);
    case "quote": return (
      <View style={{ borderLeftWidth: 3, borderLeftColor: colors.accent, paddingLeft: 10, marginVertical: 6 }}>
        {b.lines.map((l, i) => <Spans key={i} spans={l} style={{ color: colors.muted }} />)}
      </View>);
    case "code": return (
      <ScrollView horizontal style={{ marginVertical: 6, backgroundColor: "#f1ebfb", borderRadius: 6 }}>
        <Text selectable style={{ fontFamily: "monospace", fontSize: 14, color: colors.word, padding: 8 }}>{b.text}</Text>
      </ScrollView>);
    case "rule": return <View style={{ height: 1, backgroundColor: colors.line, marginVertical: 12 }} />;
  }
}

export default function BookTab() {
  const { api } = useSession();
  const { lang, script, query } = useLanguage();
  const key = "book" + lang.id + lang.updated_at + script;
  const [md, setMd] = useState<string | null>(cache.get(key) ?? null);
  const [err, setErr] = useState<string | null>(null);
  const [tocOpen, setTocOpen] = useState(false);
  const list = useRef<FlatList<Block>>(null);

  const load = async () => {
    setErr(null);
    try { const t = await api.text(`/api/conlangs/${lang.id}/grammar-book.md${query}`); cache.set(key, t); setMd(t); }
    catch (e) { setErr(errorText(e)); }
  };
  useEffect(() => { if (!md) load(); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  const parsed = useMemo(() => (md ? parseMarkdown(md) : null), [md]);

  if (err) return <View><ErrorText>{err}</ErrorText><Button title="Try again" kind="ghost" onPress={load} /></View>;
  if (!parsed) return <ActivityIndicator color={colors.accent} style={{ marginTop: 20 }} />;

  return (
    <View style={{ flex: 1 }}>
      <Button title="Contents" kind="ghost" style={{ marginBottom: 6, minHeight: 40 }} onPress={() => setTocOpen(true)} />
      <FlatList ref={list} data={parsed.blocks} keyExtractor={(_, i) => String(i)} renderItem={({ item }) => <BlockView b={item} />}
        initialNumToRender={25} windowSize={11} contentContainerStyle={{ paddingBottom: 40 }}
        onScrollToIndexFailed={(info: { index: number; averageItemLength: number }) => { list.current?.scrollToOffset({ offset: info.averageItemLength * info.index, animated: true }); }} />
      <Modal visible={tocOpen} animationType="slide" onRequestClose={() => setTocOpen(false)}>
        <View style={{ flex: 1, backgroundColor: colors.bg, paddingTop: 56, paddingHorizontal: 20 }}>
          <Text style={{ fontSize: 22, fontWeight: "700", color: colors.ink, marginBottom: 10 }}>Contents</Text>
          <ScrollView>
            {parsed.toc.map((t, i) => (
              <Pressable key={i} accessibilityRole="button" onPress={() => { setTocOpen(false); setTimeout(() => list.current?.scrollToIndex({ index: t.index, animated: true, viewPosition: 0 }), 250); }}
                style={{ paddingVertical: 9, paddingLeft: t.level === 3 ? 18 : 0 }}>
                <Text style={{ fontSize: t.level === 2 ? 17 : 15, fontWeight: t.level === 2 ? "600" : "400", color: colors.accent }}>{t.text}</Text>
              </Pressable>
            ))}
          </ScrollView>
          <Button title="Close" style={{ marginVertical: 16 }} onPress={() => setTocOpen(false)} />
        </View>
      </Modal>
    </View>
  );
}
