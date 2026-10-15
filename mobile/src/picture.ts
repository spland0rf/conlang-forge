// Choosing a picture of sample letters and measuring it on the phone. The picture is shrunk to at most 1024 pixels on a
// side, decoded, and measured exactly as the website does; only the small JPEG and the measurements are sent.
import * as ImageManipulator from "expo-image-manipulator";
import * as ImagePicker from "expo-image-picker";
import * as jpeg from "jpeg-js";
import { base64ToBytes } from "./base64";
import { measureRgba, shrunkSize, type Measures } from "./measure";

export type Picked = { uri: string; width: number; height: number };
export type Analysis = { image: { media_type: "image/jpeg"; data: string }; measures: Measures };

/** Opens the photo library. Returns null when the person cancels. */
export async function pickPicture(): Promise<Picked | null> {
  const r = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 1, allowsEditing: false });
  if (r.canceled || !r.assets || !r.assets.length) return null;
  const a = r.assets[0];
  return { uri: a.uri, width: a.width, height: a.height };
}

export async function analyzePicture(p: Picked): Promise<Analysis> {
  const out = await ImageManipulator.manipulateAsync(p.uri, [{ resize: shrunkSize(p.width, p.height) }],
    { compress: 0.88, format: ImageManipulator.SaveFormat.JPEG, base64: true });
  if (!out.base64) throw new Error("Could not read that picture.");
  const img = jpeg.decode(base64ToBytes(out.base64), { useTArray: true, formatAsRGBA: true });
  return { image: { media_type: "image/jpeg", data: out.base64 }, measures: measureRgba(img.data, img.width, img.height) };
}
