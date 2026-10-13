// Tokens and the server address live in the phone's secure storage (Keychain on iOS, Keystore on Android).
import * as SecureStore from "expo-secure-store";
import type { SessionStore } from "./api";
import type { Session } from "./types";

const SESSION_KEY = "cf.session";
const SERVER_KEY = "cf.server";

export const secureSessionStore: SessionStore = {
  async load() {
    try { const raw = await SecureStore.getItemAsync(SESSION_KEY); return raw ? (JSON.parse(raw) as Session) : null; } catch { return null; }
  },
  async save(s) {
    try { await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify({ access_token: s.access_token, refresh_token: s.refresh_token })); } catch {}
  },
  async clear() { try { await SecureStore.deleteItemAsync(SESSION_KEY); } catch {} },
};

export async function loadServer(): Promise<string | null> {
  try { return await SecureStore.getItemAsync(SERVER_KEY); } catch { return null; }
}
export async function saveServer(url: string): Promise<void> {
  try { await SecureStore.setItemAsync(SERVER_KEY, url); } catch {}
}
