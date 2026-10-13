// App-wide state: the API client, server config, and who is signed in.
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Api, createApi } from "./api";
import { DEFAULT_BASE_URL } from "./config";
import { loadServer, saveServer, secureSessionStore } from "./storage";
import type { Config, Me, Session } from "./types";

type Ctx = {
  api: Api; config: Config | null; me: Me | null; ready: boolean; configError: string | null;
  server: string; changeServer(url: string): Promise<void>;
  signIn(s: Session): Promise<void>; signOut(): Promise<void>; reloadConfig(): Promise<void>; reloadMe(): Promise<void>;
};
const C = createContext<Ctx>(null as any);
export const useSession = () => useContext(C);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [server, setServer] = useState(DEFAULT_BASE_URL);
  const meRef = useRef<(m: Me | null) => void>(setMe);

  const api = useMemo(() => createApi({ baseUrl: DEFAULT_BASE_URL, store: secureSessionStore, onSignedOut: () => meRef.current(null) }), []);

  const reloadConfig = useCallback(async () => {
    try { setConfig(await api.get<Config>("/api/config")); setConfigError(null); }
    catch { setConfig(null); setConfigError("Could not reach the server at " + api.baseUrl); }
  }, [api]);

  const reloadMe = useCallback(async () => {
    const s = await secureSessionStore.load();
    if (!s) { setMe(null); return; }
    try { setMe(await api.get<Me>("/api/me")); } catch { setMe(null); }
  }, [api]);

  useEffect(() => {
    (async () => {
      const saved = await loadServer();
      if (saved) { api.setBaseUrl(saved); setServer(api.baseUrl); }
      await reloadConfig();
      await reloadMe();
      setReady(true);
    })();
  }, [api, reloadConfig, reloadMe]);

  const value: Ctx = {
    api, config, me, ready, configError, server,
    async changeServer(url) { api.setBaseUrl(url); setServer(api.baseUrl); await saveServer(api.baseUrl); await secureSessionStore.clear(); setMe(null); await reloadConfig(); },
    async signIn(s) { await secureSessionStore.save(s); await reloadMe(); },
    async signOut() {
      const s = await secureSessionStore.load();
      try { if (s) await api.post("/api/auth/logout", { refresh_token: s.refresh_token }); } catch {}
      await secureSessionStore.clear(); setMe(null);
    },
    reloadConfig, reloadMe,
  };
  return <C.Provider value={value}>{children}</C.Provider>;
}
