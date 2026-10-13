import React, { useCallback, useEffect, useState } from "react";
import { FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import { errorText, TYPES } from "../format";
import { useSession } from "../session";
import type { LanguageSummary } from "../types";
import { Button, Card, ErrorText, H1, Muted } from "../ui/components";
import { colors } from "../ui/theme";

export default function LanguagesScreen({ onOpen, refreshKey = 0 }: { onOpen: (l: LanguageSummary) => void; refreshKey?: number }) {
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
    <View style={{ flex: 1, backgroundColor: colors.bg, paddingTop: 56 }}>
      <View style={{ paddingHorizontal: 20, flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <H1>Your languages</H1>
        <Text accessibilityRole="button" onPress={signOut} style={{ color: colors.accent, fontSize: 15 }}>Sign out</Text>
      </View>
      <Muted style={{ paddingHorizontal: 20, marginBottom: 8 }}>{me?.email}</Muted>
      <ErrorText>{err}</ErrorText>
      <FlatList
        data={items ?? []} keyExtractor={(l) => l.id} contentContainerStyle={{ padding: 20, paddingTop: 8 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}
        ListEmptyComponent={items === null ? <Muted>Loading…</Muted> : (
          <Card>
            <Text style={{ fontSize: 16, color: colors.ink, marginBottom: 6 }}>No languages yet.</Text>
            <Muted>Create one on the website for now; creating languages arrives in this app soon.</Muted>
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
