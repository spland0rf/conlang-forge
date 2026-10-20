import React, { useCallback, useEffect, useState } from "react";
import { FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import { errorText, TYPES } from "../format";
import { useSession } from "../session";
import type { LanguageSummary } from "../types";
import { Button, Card, ErrorText, H1, Muted } from "../ui/components";
import DeleteAccount from "./DeleteAccount";
import { colors } from "../ui/theme";

export default function LanguagesScreen({ onOpen, refreshKey = 0, onNew }: { onOpen: (l: LanguageSummary) => void; refreshKey?: number; onNew: (how: "forge" | "sample") => void }) {
  const { api, me, signOut } = useSession();
  const [items, setItems] = useState<LanguageSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    try { setItems((await api.get<{ conlangs: LanguageSummary[] }>("/api/conlangs")).conlangs); }
    catch (e) { setErr(errorText(e)); setItems((x) => x ?? []); }
  }, [api]);
  useEffect(() => { load(); }, [load, refreshKey]);

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg, paddingTop: 16 }}>
      <View style={{ paddingHorizontal: 20, flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <H1>Your languages</H1>
        <Text accessibilityRole="button" onPress={signOut} style={{ color: colors.accent, fontSize: 15 }}>Sign out</Text>
      </View>
      <Muted style={{ paddingHorizontal: 20, marginBottom: 8 }}>{me?.email}</Muted>
      <DeleteAccount />
      <View style={{ paddingHorizontal: 20 }}>
        <Card>
          <Text style={{ fontSize: 17, fontWeight: "700", color: colors.ink, marginBottom: 4 }}>Create a language</Text>
          <Muted style={{ marginBottom: 10 }}>Pick a few settings or just press the button, or start from a sample of text.</Muted>
          <View style={{ gap: 8 }}>
            <Button title="Forge a language" onPress={() => onNew("forge")} />
            <Button title="Start from a sample" kind="ghost" onPress={() => onNew("sample")} />
          </View>
        </Card>
      </View>
      <ErrorText>{err}</ErrorText>
      <FlatList
        data={items ?? []} keyExtractor={(l) => l.id} contentContainerStyle={{ padding: 20, paddingTop: 8 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}
        ListEmptyComponent={items === null ? <Muted>Loading…</Muted> : (
          <Card>
            <Text style={{ fontSize: 16, color: colors.ink, marginBottom: 6 }}>No languages yet.</Text>
            <Muted>Create your first one above.</Muted>
            <Button title="Refresh" kind="ghost" style={{ marginTop: 12 }} onPress={load} />
          </Card>
        )}
        renderItem={({ item }) => (
          <Pressable accessibilityRole="button" accessibilityLabel={"Open " + item.name} onPress={() => onOpen(item)}>
            <Card>
              <Text style={{ fontSize: 20, fontWeight: "700", color: colors.word }}>{item.name}</Text>
              <Muted>{[item.typology && (TYPES[item.typology] || item.typology), item.word_order].filter(Boolean).join(" · ")}</Muted>
            </Card>
          </Pressable>
        )}
      />
    </View>
  );
}
