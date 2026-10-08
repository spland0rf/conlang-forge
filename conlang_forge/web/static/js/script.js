// Which letters to draw words with. Only a view: the language is stored as sounds, never as one spelling.
const KEY = "cf.script";
export function getScript() { try { return localStorage.getItem(KEY) === "special" ? "special" : "plain"; } catch { return "plain"; } }
export function setScript(s) { try { localStorage.setItem(KEY, s); } catch {} }
export const sq = (sep = "?") => (getScript() === "special" ? `${sep}script=special` : "");
