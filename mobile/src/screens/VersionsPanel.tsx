// Checkpoints of a language or a writing system. Nothing is kept automatically: "Create checkpoint" stores the current
// state read only as the next numbered version, and the item carries on as the editable working version. "New version
// from this one" makes a separate editable copy that starts identical to an old checkpoint.
import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, Text, View } from "react-native";
import { errorText } from "../format";
import { useSession } from "../session";
import { kb, versionBase } from "../scriptsModel";
import type { BranchResult, VersionChange, VersionDetail, VersionList, VersionRow } from "../types";
import { Button, Card, ErrorText, Field, Muted, OkText } from "../ui/components";
import { SvgView } from "../ui/SvgView";
import { colors } from "../ui/theme";

const when = (ms: number) => new Date(ms).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

function Changes({ list }: { list: VersionChange[] }) {
  if (!list || !list.length) return <Muted>The working version has no differences from this checkpoint.</Muted>;
  return (
    <View style={{ marginTop: 6 }}>
      <Text style={{ fontWeight: "600", color: colors.ink, marginBottom: 4 }}>{`What the working version has changed since (${list.length})`}</Text>
      {list.map((c, i) => (
        <View key={i} style={{ flexDirection: "row", paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: colors.line }}>
          <Text style={{ width: 110, color: colors.muted, fontSize: 13 }}>{c.label}</Text>
          <Text style={{ flex: 1, fontSize: 13, color: colors.muted }}>{String(c.then)}</Text>
          <Text style={{ fontSize: 13, color: colors.muted }}> → </Text>
          <Text style={{ flex: 1, fontSize: 13, color: colors.word }}>{String(c.now)}</Text>
        </View>
      ))}
    </View>
  );
}

function Detail({ d }: { d: VersionDetail }) {
  return (
    <Card style={{ backgroundColor: "#f1ebfb" }}>
      <Text style={{ fontSize: 14, color: colors.ink }}>{`v${d.n}${d.label ? " · " + d.label : ""} · kept ${when(d.created_at)} · read only`}</Text>
      {d.kind === "conlang" ? (
        <View style={{ marginTop: 6 }}>
          <Text style={{ color: colors.ink }}>{`${d.name} · seed ${d.seed} · ${d.words ?? 0} words · ${(d.consonants || []).length} consonants, ${(d.vowels || []).length} vowels${d.typology ? " · " + d.typology : ""}${d.word_order ? " · word order " + d.word_order : ""}`}</Text>
          <Text style={{ color: colors.word, fontSize: 16, marginTop: 4 }}>{[...(d.consonants || []), ...(d.vowels || [])].join(" ")}</Text>
        </View>
      ) : (
        <View style={{ marginTop: 6 }}>
          <Text style={{ color: colors.ink, marginBottom: 6 }}>{`${d.name} · seed ${d.seed}`}</Text>
          {d.sample ? <SvgView xml={d.sample} /> : null}
          {(d.sentences || []).map((s, i) => (
            <View key={i} style={{ marginTop: 8 }}><Muted>{s.english}</Muted><SvgView xml={s.svg} /></View>
          ))}
          {d.specimen ? <View style={{ marginTop: 10 }}><Muted>Letters at this checkpoint</Muted><SvgView xml={d.specimen} /></View> : null}
        </View>
      )}
      <Changes list={d.changes_since} />
    </Card>
  );
}

/** kind: "lang" or "script". prepare() may save pending edits first and returns false to stop. */
export default function VersionsPanel({ kind, id, prepare, onOpenCopy }: {
  kind: "lang" | "script"; id: string; prepare?: () => Promise<boolean>; onOpenCopy: (r: BranchResult) => void;
}) {
  const { api } = useSession();
  const base = versionBase(kind, id);
  const noun = kind === "lang" ? "language" : "writing system";
  const [state, setState] = useState<VersionList | null>(null);
  const [note, setNote] = useState("");
  const [shown, setShown] = useState<number | null>(null);
  const [detail, setDetail] = useState<VersionDetail | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setState(await api.get<VersionList>(`${base}/versions`)); } catch (e) { setErr(errorText(e)); }
  }, [api, base]);
  useEffect(() => { load(); }, [load]);

  const create = async () => {
    setErr(null); setOk(null); setBusy("create");
    try {
      if (prepare && !(await prepare())) return;
      const s = await api.post<VersionList>(`${base}/versions`, { label: note });
      setState(s); setNote(""); setShown(null); setDetail(null);
      setOk(`Checkpoint v${s.versions[0].n} kept. You are now editing v${s.working}.`);
    } catch (e) { setErr(errorText(e)); } finally { setBusy(null); }
  };

  const view = async (n: number) => {
    if (shown === n) { setShown(null); setDetail(null); return; }
    setShown(n); setDetail(null); setErr(null); setBusy("view" + n);
    try { setDetail(await api.get<VersionDetail>(`${base}/versions/${n}`)); } catch (e) { setErr(errorText(e)); } finally { setBusy(null); }
  };

  const branch = (v: VersionRow) => Alert.alert(`New version from v${v.n}?`,
    `This makes a separate, editable ${noun} that starts identical to v${v.n}. Your current working version is not changed.`, [
      { text: "Cancel", style: "cancel" },
      { text: "Create it", onPress: async () => {
        setErr(null); setBusy("branch" + v.n);
        try {
          const r = await api.post<BranchResult>(`${base}/versions/${v.n}/branch`, {});
          if (r.exact === false) Alert.alert("Made, with a difference", "The letter generator has changed since this checkpoint, so the new copy is redrawn slightly differently.");
          onOpenCopy(r);
        } catch (e) { setErr(errorText(e)); } finally { setBusy(null); }
      } },
    ]);

  const remove = (v: VersionRow) => Alert.alert(`Delete checkpoint v${v.n}?`, "The checkpoint is removed for good. Your working version is not affected.", [
    { text: "Cancel", style: "cancel" },
    { text: "Delete", style: "destructive", onPress: async () => {
      try { setState(await api.del<VersionList>(`${base}/versions/${v.n}`)); setShown(null); setDetail(null); } catch (e) { setErr(errorText(e)); }
    } },
  ]);

  if (!state) return err ? <ErrorText>{err}</ErrorText> : <ActivityIndicator color={colors.accent} />;
  return (
    <View>
      <Muted style={{ marginBottom: 8 }}>{`A checkpoint keeps this ${noun} exactly as it is now, read only, so you can look back or start a new version from it. Nothing is kept automatically. You carry on editing the working version.`}</Muted>
      {state.branched_from ? <Muted style={{ marginBottom: 6 }}>{`Started as a new version from “${state.branched_from.name}” v${state.branched_from.n}.`}</Muted> : null}
      <Text style={{ color: colors.ink, marginBottom: 8 }}>
        <Text style={{ fontWeight: "700" }}>{state.has_checkpoints ? `Working version: v${state.working}` : "Working version"}</Text>
        <Text style={{ color: colors.muted }}>{state.has_checkpoints ? " (editable)" : " (no checkpoints yet)"}</Text>
      </Text>
      <Field label="Note (optional)" value={note} onChangeText={setNote} maxLength={80} placeholder="e.g. before the new vowels" />
      <Button title="Create checkpoint" busy={busy === "create"} onPress={create} />
      <ErrorText>{err}</ErrorText>
      <OkText>{ok}</OkText>
      <View style={{ marginTop: 14 }}>
        {state.versions.length === 0 ? <Muted>No checkpoints yet. Nothing is kept unless you press the button above.</Muted> : state.versions.map((v) => (
          <View key={v.id} style={{ paddingVertical: 10, borderTopWidth: 1, borderTopColor: colors.line }}>
            <Text style={{ color: colors.ink }}><Text style={{ fontWeight: "700" }}>{`v${v.n}`}</Text>{v.label ? ` · ${v.label}` : ""}</Text>
            <Muted>{`${when(v.created_at)} · ${kb(v.stored_bytes)}`}</Muted>
            <View style={{ flexDirection: "row", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
              <Button title={shown === v.n ? "Hide" : "View"} kind="ghost" busy={busy === "view" + v.n} onPress={() => view(v.n)} />
              <Button title="New version from this one" kind="ghost" busy={busy === "branch" + v.n} onPress={() => branch(v)} />
              <Button title="Delete" kind="ghost" onPress={() => remove(v)} />
            </View>
            {shown === v.n && detail ? <View style={{ marginTop: 10 }}><Detail d={detail} /></View> : null}
          </View>
        ))}
      </View>
    </View>
  );
}
