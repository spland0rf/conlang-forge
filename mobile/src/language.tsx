// The language being viewed: its full details, the letters shown (plain or special), and a way to reload it.
import React, { createContext, useContext } from "react";
import type { Language, Script } from "./types";

type Ctx = { lang: Language; script: Script; setScript(s: Script): void; reload(): Promise<void>; query: string };
const C = createContext<Ctx>(null as any);
export const useLanguage = () => useContext(C);
export const LanguageProvider = ({ value, children }: { value: Ctx; children: React.ReactNode }) => <C.Provider value={value}>{children}</C.Provider>;

/** "?script=special" or "" — how the website asks for the other spelling. */
export const scriptQuery = (s: Script) => (s === "special" ? "?script=special" : "");
