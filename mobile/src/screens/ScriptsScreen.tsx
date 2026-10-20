// The Writing systems list: the user's own scripts, and a way to design a new one. Mirrors the website's list page.
import React, { useCallback, useEffect, useState } from "react";
import { FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import { errorText } from "../format";
import { useSession } from "../session";
import type { ScriptRecord } from "../types";
import { Button, Card, ErrorText, H1, Muted } from "../ui/components";
import { colors } from "../ui/theme";
import { HOW_OPTIONS, type HowToMake } from "../scriptsModel";

export default function ScriptsScreen({ onOpen, onNew, refreshKey = 0 }: { onOpen: (id: string) => void; onNew: (how: HowToMake) => void; refreshKey?: number }) {
  const { api } = useSession();
  const [items, setItems] = useState<ScriptRecord[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    try { setItems((await api.get<{ scripts: ScriptRecord[] }>("/api/scripts")).scripts); }
    catch (e) { setErr(errorText(e)); setItems((x) => x ?? []); }
  }, [api]);
  useEffect(() => { load(); }, [load, refreshKey]);

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg, paddingTop: 16 }}>
      <View style={{ paddingHorizontal: 20 }}>
        <H1>Writing systems</H1>
        <Muted style={{ marginBottom: 10 }}>Design a script, tie it to a language so it has a letter for every sound, and set it as that language's primary script. Any script can also write any of your languages, using its closest sounds.</Muted>
        <Card>
          <Text style={{ fontSize: 17, fontWeight: "700", color: colors.ink, marginBottom: 4 }}>Create a writing system</Text>
          <Muted style={{ marginBottom: 10 }}>Choose how it should look. You can change any of it afterwards.</Muted>
          <View style={{ gap: 8 }}>
            {HOW_OPTIONS.map(([k, label], i) => <Button key={k} title={label} kind={i === 0 ? "primary" : "ghost"} onPress={() => onNew(k)} />)}
          </View>
        </Card>
      </View>
      <ErrorText>{err}</ErrorText>
      <FlatList
        data={items ?? []} keyExtractor={(s) => s.id} contentContainerStyle={{ padding: 20, paddingTop: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}
        ListEmptyComponent={items === null ? <Muted>Loading…</Muted> : <Muted>You have not saved a writing system yet. Create one above, then link it to a language as its own script.</Muted>}
        renderItem={({ item }) => (
          <Pressable accessibilityRole="button" accessibilityLabel={"Open " + item.name} onPress={() => onOpen(item.id)}>
            <Card>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                <Text style={{ fontSize: 18, fontWeight: "700", color: colors.word, flex: 1 }}>{item.name}</Text>
                {item.primary ? <Text style={{ fontSize: 12, color: colors.accentInk, backgroundColor: colors.accent, paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10, overflow: "hidden" }}>primary</Text> : null}
              </View>
              <Muted>{item.conlang_name ? `designed for ${item.conlang_name}` : "not tied to a language"}</Muted>
            </Card>
          </Pressable>
        )}
      />
    </View>
  );
}
