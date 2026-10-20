// A picture of written text with "Download image" (PNG) and "SVG" buttons, like the website's download buttons.
import React, { useRef, useState } from "react";
import { View } from "react-native";
import ViewShot from "react-native-view-shot";
import { errorText } from "../format";
import { fileSlug, shareFileUri, shareTextFile } from "../share";
import { Button, ErrorText, Muted } from "./components";
import { SvgView } from "./SvgView";

export function WrittenImage({ svg, name }: { svg: string; name: string }) {
  const shot = useRef<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const base = fileSlug(name) + "-writing";
  const png = async () => {
    setErr(null); setBusy(true);
    try { const uri = await shot.current.capture(); await shareFileUri(uri, "image/png", base + ".png"); }
    catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
  };
  const vector = async () => { setErr(null); try { await shareTextFile(base + ".svg", svg, "image/svg+xml"); } catch (e) { setErr(errorText(e)); } };
  return (
    <View>
      <ViewShot ref={shot} options={{ format: "png", quality: 1, result: "tmpfile" }} style={{ backgroundColor: "#fff", borderRadius: 8, padding: 4 }}>
        <SvgView xml={svg} />
      </ViewShot>
      <ErrorText>{err}</ErrorText>
      <View style={{ flexDirection: "row", gap: 10, marginTop: 8 }}>
        <Button title="Download image" busy={busy} style={{ flex: 1 }} onPress={png} />
        <Button title="SVG file" kind="ghost" onPress={vector} />
      </View>
      <Muted style={{ marginTop: 6 }}>The SVG is a vector file for design tools, email, Drive or Files. Messaging apps usually accept only the image.</Muted>
    </View>
  );
}
