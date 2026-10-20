// A picture of written text with Share and Save PNG buttons (the image) and Save SVG (the vector file).
import React, { useRef, useState } from "react";
import { Pressable, View } from "react-native";
import { SvgXml } from "react-native-svg";
import ViewShot from "react-native-view-shot";
import { errorText } from "../format";
import { fileSlug, savePictureFile, saveTextFile, shareFileUri } from "../share";
import { Button, ErrorText, Muted } from "./components";
import { SvgView } from "./SvgView";
import { colors } from "./theme";

// The usual share symbol: three dots joined by two lines.
const SHARE_ICON = (c: string) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="${c}" stroke="${c}" stroke-width="1.6" stroke-linecap="round"><circle cx="18" cy="5" r="2.6"/><circle cx="6" cy="12" r="2.6"/><circle cx="18" cy="19" r="2.6"/><path d="M8.3 10.8L15.7 6.2M8.3 13.2L15.7 17.8" fill="none"/></g></svg>`;

export function WrittenImage({ svg, name }: { svg: string; name: string }) {
  const shot = useRef<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const base = fileSlug(name) + "-writing";
  const [saved, setSaved] = useState<string | null>(null);
  const sharePng = async () => {
    setErr(null); setSaved(null); setBusy(true);
    try { const uri = await shot.current.capture(); await shareFileUri(uri, "image/png", base + ".png"); }
    catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  };
  const savePng = async () => {
    setErr(null); setSaved(null); setBusy(true);
    try { const uri = await shot.current.capture(); if (await savePictureFile(uri, base + ".png", "image/png")) setSaved(`Saved ${base}.png`); }
    catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  };
  const save = async () => {
    setErr(null); setSaved(null);
    try { if (await saveTextFile(base + ".svg", svg, "image/svg+xml")) setSaved(`Saved ${base}.svg`); } catch (e) { setErr(errorText(e)); }
  };
  return (
    <View>
      <ViewShot ref={shot} options={{ format: "png", quality: 1, result: "tmpfile" }} style={{ backgroundColor: "#fff", borderRadius: 8, padding: 4 }}>
        <SvgView xml={svg} />
      </ViewShot>
      <ErrorText>{err}</ErrorText>
      <View style={{ flexDirection: "row", gap: 10, marginTop: 8, alignItems: "center" }}>
        <Pressable accessibilityRole="button" accessibilityLabel="Share image" onPress={busy ? undefined : sharePng}
          style={({ pressed }: { pressed: boolean }) => ({ width: 48, height: 48, borderRadius: 10, backgroundColor: colors.accent, alignItems: "center", justifyContent: "center", opacity: busy ? 0.5 : pressed ? 0.8 : 1 })}>
          <SvgXml xml={SHARE_ICON(colors.accentInk)} width={24} height={24} />
        </Pressable>
        <Button title="Save PNG" busy={busy} style={{ flex: 1 }} onPress={savePng} />
      </View>
      <View style={{ flexDirection: "row", gap: 10, marginTop: 8 }}>
        <Button title="Save SVG" kind="ghost" style={{ flex: 1 }} onPress={save} />
      </View>
      <Muted style={{ marginTop: 6 }}>{saved ?? "Save puts the file in a folder you choose (Files, Drive, Downloads). Share sends the image only."}</Muted>
    </View>
  );
}
