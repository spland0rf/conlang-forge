// The phone-specific pieces for Google sign-in (browser sheet, secure random, SHA-256).
import * as Crypto from "expo-crypto";
import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import type { Api } from "./api";
import { googleSignIn } from "./googleAuth";

WebBrowser.maybeCompleteAuthSession();

const b64url = (b64: string) => b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

export function signInWithGoogle(api: Api) {
  return googleSignIn({
    api,
    redirectUri: Linking.createURL("auth"),          // conlangforge://auth in a built app, exp://…/--/auth in Expo Go
    openAuth: (url, redirect) => WebBrowser.openAuthSessionAsync(url, redirect),
    randomVerifier: async () => b64url(btoa(String.fromCharCode(...(await Crypto.getRandomBytesAsync(32))))),
    sha256Base64Url: async (t) => b64url(await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, t, { encoding: Crypto.CryptoEncoding.BASE64 })),
  });
}
