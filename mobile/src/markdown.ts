// A small Markdown reader for the generated grammar book. Pure data out (no React), so it is tested with plain Node.
// Supports what the book uses: headings, paragraphs, bullet/numbered lists, tables, quotes, code blocks, rules,
// **bold**, *italic*, `code` and [links](...). The <details>/<summary> tags are flattened into a bold line.

export type Span = { text: string; bold?: boolean; italic?: boolean; code?: boolean; href?: string };
export type Block =
  | { kind: "heading"; level: number; spans: Span[]; id: string; text: string }
  | { kind: "paragraph"; spans: Span[] }
  | { kind: "list"; ordered: boolean; items: Span[][] }
  | { kind: "table"; head: Span[][] | null; rows: Span[][][] }
  | { kind: "quote"; lines: Span[][] }
  | { kind: "code"; text: string }
  | { kind: "rule" };
export type TocItem = { level: number; text: string; index: number };

export function inline(src: string): Span[] {
  const out: Span[] = [];
  const re = /`([^`]+)`|\*\*([^*]+)\*\*|(^|[^*])\*([^*\s][^*]*)\*|\[([^\]]+)\]\((https?:\/\/[^)\s]+|#[^)\s]*)\)/g;
  let last = 0, m: RegExpExecArray | null;
  const push = (t: string, extra: Partial<Span> = {}) => { if (t) out.push({ text: t, ...extra }); };
  while ((m = re.exec(src))) {
    if (m[3] !== undefined) {                       // *italic*: keep the character in front of it
      push(src.slice(last, m.index) + m[3]);
      push(m[4], { italic: true });
    } else {
      push(src.slice(last, m.index));
      if (m[1] !== undefined) push(m[1], { code: true });
      else if (m[2] !== undefined) push(m[2], { bold: true });
      else push(m[5], { href: m[6] });
    }
    last = m.index + m[0].length;
  }
  push(src.slice(last));
  return out;
}

const plain = (s: string) => s.replace(/[*`]/g, "");
const slug = (s: string) => plain(s).toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "");
const cells = (line: string) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());

export function parseMarkdown(md: string): { blocks: Block[]; toc: TocItem[] } {
  const lines = md.replace(/\r/g, "").split("\n");
  const blocks: Block[] = [], toc: TocItem[] = [];
  const listRe = /^\s*([-*]|\d+\.)\s+/;
  let i = 0;
  while (i < lines.length) {
    const line = lines[i].replace(/^\s*<details>(?=<summary>)/, "");           // "<details><summary>Answer key</summary>" on one line
    if (/^```/.test(line)) {
      const buf: string[] = []; i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++; blocks.push({ kind: "code", text: buf.join("\n") }); continue;
    }
    if (/^<\/?details>\s*$/.test(line.trim())) { i++; continue; }
    const sm = line.trim().match(/^<summary>(.*)<\/summary>$/);
    if (sm) { blocks.push({ kind: "paragraph", spans: inline(sm[1]).map((s) => ({ ...s, bold: true })) }); i++; continue; }
    const hm = line.match(/^(#{1,4})\s+(.*)$/);
    if (hm) {
      const level = hm[1].length;
      if (level === 2 || level === 3) toc.push({ level, text: plain(hm[2]), index: blocks.length });
      blocks.push({ kind: "heading", level, spans: inline(hm[2]), id: slug(hm[2]), text: plain(hm[2]) }); i++; continue;
    }
    if (/^---+\s*$/.test(line)) { blocks.push({ kind: "rule" }); i++; continue; }
    if (/^\|/.test(line) && i + 1 < lines.length && /^\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const head = cells(line); i += 2;
      const rows: Span[][][] = [];
      while (i < lines.length && /^\|/.test(lines[i])) rows.push(cells(lines[i++]).map(inline));
      const empty = head.every((c) => !c);
      blocks.push({ kind: "table", head: empty ? null : head.map(inline), rows }); continue;
    }
    if (/^>\s?/.test(line)) {
      const buf: Span[][] = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) buf.push(inline(lines[i++].replace(/^>\s?/, "")));
      blocks.push({ kind: "quote", lines: buf }); continue;
    }
    if (listRe.test(line)) {
      const ordered = /^\s*\d+\./.test(line), items: Span[][] = [];
      while (i < lines.length && listRe.test(lines[i])) items.push(inline(lines[i++].replace(listRe, "")));
      blocks.push({ kind: "list", ordered, items }); continue;
    }
    if (!line.trim()) { i++; continue; }
    const buf: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^(```|#{1,4}\s|\||>|---|<\/?details|<summary|\s*([-*]|\d+\.)\s)/.test(lines[i])) buf.push(lines[i++]);
    if (!buf.length) buf.push(lines[i++]);
    blocks.push({ kind: "paragraph", spans: inline(buf.join(" ")) });
  }
  // the book's own title is shown by the screen
  if (blocks[0]?.kind === "heading" && blocks[0].level === 1) {
    blocks.shift();
    toc.forEach((t) => { t.index -= 1; });
  }
  return { blocks, toc };
}
