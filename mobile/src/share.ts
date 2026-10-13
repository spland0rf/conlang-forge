// Hand a text file to the phone's share sheet (save to Files, Drive, email, ...). Falls back to sharing plain text.
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { Share } from "react-native";

export const safeName = (name: string) => name.normalize("NFKD").replace(/[^\x00-\x7F]/g, "").replace(/\W+/g, "_").replace(/^_|_$/g, "") || "language";

export async function shareTextFile(filename: string, content: string, mimeType: string) {
  try {
    const file = new File(Paths.cache, filename);
    if (file.exists) file.delete();
    file.create();
    file.write(content);
    if (await Sharing.isAvailableAsync()) {
      await Sharing.shareAsync(file.uri, { mimeType, dialogTitle: filename, UTI: mimeType === "text/csv" ? "public.comma-separated-values-text" : "net.daringfireball.markdown" });
      return;
    }
  } catch { /* fall through to sharing the text itself */ }
  await Share.share({ title: filename, message: content });
}
