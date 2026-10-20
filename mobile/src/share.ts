// Hand a text file to the phone's share sheet (save to Files, Drive, email, ...). Falls back to sharing plain text.
import { Directory, File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { Share } from "react-native";

export const safeName = (name: string) => name.normalize("NFKD").replace(/[^\x00-\x7F]/g, "").replace(/\W+/g, "_").replace(/^_|_$/g, "") || "language";

export const fileSlug = (name: string) => (name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "writing");

/** Share a picture file the phone has already written (for example a screenshot of the written text). */
export async function shareFileUri(uri: string, mimeType: string, title: string) {
  if (await Sharing.isAvailableAsync()) { await Sharing.shareAsync(uri, { mimeType, dialogTitle: title, UTI: mimeType === "image/png" ? "public.png" : "public.svg-image" }); return; }
  throw new Error("Sharing is not available on this device.");
}

export async function shareTextFile(filename: string, content: string, mimeType: string) {
  try {
    const file = new File(Paths.cache, filename);
    if (file.exists) file.delete();
    file.create();
    file.write(content);
    if (await Sharing.isAvailableAsync()) {
      await Sharing.shareAsync(file.uri, { mimeType, dialogTitle: filename, UTI: ({ "text/csv": "public.comma-separated-values-text", "application/json": "public.json", "image/svg+xml": "public.svg-image" } as Record<string, string>)[mimeType] || "net.daringfireball.markdown" });
      return;
    }
  } catch { /* fall through to sharing the text itself */ }
  await Share.share({ title: filename, message: content });
}

/** Save a text file into a folder the person picks with the system file picker (Files, Drive, Downloads...). This is the
 * reliable way to keep an SVG: the share sheet only offers apps that declare they accept the type, and messaging apps accept
 * any image type. Returns false if the person cancelled the picker. Falls back to the share sheet if the picker is missing. */
export async function saveTextFile(filename: string, content: string, mimeType: string): Promise<boolean> {
  const picker = (Directory as any)?.pickDirectoryAsync;
  if (typeof picker !== "function") { await shareTextFile(filename, content, mimeType); return true; }
  let dir: any;
  try { dir = await picker.call(Directory); } catch { return false; }        // cancelled
  if (!dir) return false;
  const file = dir.createFile(filename, mimeType);
  file.write(content);
  return true;
}
