// Charts for the administrator's usage page, drawn with plain views: stacked columns over time and ranked bars. Colour
// is identity (a fixed order, never cycled), a legend is always shown, tapping a column shows its numbers, and a table
// view is one tap away for anyone who prefers numbers. Mirrors the website's charts.js.
import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { type Bucket, bucketTotal, compact, labelEvery, niceMax } from "../adminModel";
import { Muted } from "./components";
import { colors } from "./theme";

export type Series = { key: string; label: string; color: string };
const H = 170, GRID = 4;

function Legend({ series }: { series: Series[] }) {
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12, marginTop: 8 }}>
      {series.map((s) => (
        <View key={s.key} style={{ flexDirection: "row", alignItems: "center", gap: 5 }}>
          <View style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: s.color }} />
          <Text style={{ fontSize: 12, color: colors.muted }}>{s.label}</Text>
        </View>
      ))}
    </View>
  );
}

export function StackedColumns({ title, note, buckets, series, format = compact }: { title: string; note?: string; buckets: Bucket[]; series: Series[]; format?: (v: number) => string }) {
  const [sel, setSel] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const keys = series.map((s) => s.key);
  const max = niceMax(Math.max(0, ...buckets.map((b) => bucketTotal(b, keys))));
  const every = labelEvery(buckets.length);
  const picked = sel != null ? buckets[sel] : null;
  const detail = picked
    ? `${picked.label}: ${format(bucketTotal(picked, keys))} in all` + series.filter((s) => picked.parts[s.key]).map((s) => ` · ${s.label} ${format(picked.parts[s.key])}`).join("")
    : "Tap a day for its numbers.";
  return (
    <View style={{ marginBottom: 20 }}>
      <Text accessibilityRole="header" style={{ fontSize: 17, fontWeight: "600", color: colors.ink }}>{title}</Text>
      {note ? <Muted>{note}</Muted> : null}
      {table ? (
        <View style={{ marginTop: 8 }}>
          {buckets.map((b, i) => (
            <View key={i} style={{ flexDirection: "row", paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: colors.line }}>
              <Text style={{ width: 70, color: colors.muted, fontSize: 13 }}>{b.label}</Text>
              <Text style={{ width: 60, color: colors.ink, fontSize: 13 }}>{format(bucketTotal(b, keys))}</Text>
              <Text style={{ flex: 1, color: colors.muted, fontSize: 12 }}>{series.filter((s) => b.parts[s.key]).map((s) => `${s.label} ${format(b.parts[s.key])}`).join(" · ")}</Text>
            </View>
          ))}
        </View>
      ) : (
        <View style={{ marginTop: 10, flexDirection: "row" }}>
          <View style={{ width: 38, height: H, justifyContent: "space-between", alignItems: "flex-end", paddingRight: 6 }}>
            {Array.from({ length: GRID + 1 }, (_, i) => <Text key={i} style={{ fontSize: 10, color: colors.muted }}>{format((max / GRID) * (GRID - i))}</Text>)}
          </View>
          <View style={{ flex: 1 }}>
            <View style={{ height: H, flexDirection: "row", alignItems: "flex-end", borderBottomWidth: 1.5, borderBottomColor: colors.line }}>
              {Array.from({ length: GRID }, (_, i) => <View key={i} pointerEvents="none" style={{ position: "absolute", left: 0, right: 0, top: (H / GRID) * i, height: 1, backgroundColor: colors.line }} />)}
              {buckets.map((b, i) => {
                const segs = series.filter((s) => b.parts[s.key]);
                return (
                  <Pressable key={i} accessibilityRole="button" accessibilityLabel={`${b.label}: ${format(bucketTotal(b, keys))}`} onPress={() => setSel(sel === i ? null : i)}
                    style={{ flex: 1, height: H, justifyContent: "flex-end", paddingHorizontal: buckets.length > 30 ? 0.5 : 2, opacity: sel != null && sel !== i ? 0.45 : 1 }}>
                    {[...segs].reverse().map((s, k) => (
                      <View key={s.key} style={{ height: Math.max(1.5, (b.parts[s.key] / max) * H), marginTop: k ? 2 : 0, backgroundColor: s.color, borderTopLeftRadius: k === 0 ? 3 : 0, borderTopRightRadius: k === 0 ? 3 : 0 }} />
                    ))}
                  </Pressable>
                );
              })}
            </View>
            <View style={{ flexDirection: "row", marginTop: 4 }}>
              {buckets.map((b, i) => <Text key={i} numberOfLines={1} style={{ flex: 1, fontSize: 9, color: colors.muted, textAlign: "center" }}>{i % every === 0 ? b.label : ""}</Text>)}
            </View>
          </View>
        </View>
      )}
      {!table ? <Text style={{ fontSize: 13, color: colors.ink, marginTop: 8, minHeight: 36 }}>{detail}</Text> : null}
      <Legend series={series} />
      <Text accessibilityRole="button" onPress={() => { setTable(!table); setSel(null); }} style={{ color: colors.accent, marginTop: 8 }}>{table ? "Show as chart" : "Show as table"}</Text>
    </View>
  );
}

export function RankedBars({ title, note, rows, format = compact }: { title: string; note?: string; rows: { label: string; value: number; tip?: string }[]; format?: (v: number) => string }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <View style={{ marginBottom: 20 }}>
      <Text accessibilityRole="header" style={{ fontSize: 17, fontWeight: "600", color: colors.ink }}>{title}</Text>
      {note ? <Muted>{note}</Muted> : null}
      {rows.length ? rows.map((r, i) => (
        <View key={i} style={{ marginTop: 8 }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <Text numberOfLines={1} style={{ color: colors.ink, fontSize: 14, flex: 1 }}>{r.label}</Text>
            <Text style={{ color: colors.muted, fontSize: 13 }}>{format(r.value)}</Text>
          </View>
          <View style={{ height: 12, borderRadius: 4, backgroundColor: colors.line, marginTop: 3, overflow: "hidden" }}>
            <View style={{ width: `${Math.max(1.5, (r.value / max) * 100)}%`, height: 12, backgroundColor: "#2a78d6", borderRadius: 4 }} />
          </View>
          {r.tip ? <Muted>{r.tip}</Muted> : null}
        </View>
      )) : <Muted style={{ marginTop: 6 }}>Nothing yet in this period.</Muted>}
    </View>
  );
}
