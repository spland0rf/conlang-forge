// A small, safe Markdown renderer for the generated books: everything is escaped except the few constructs below.
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const slug = (s) => s.toLowerCase().replace(/<[^>]*>/g, "").replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "");

function inline(s) {
  s = esc(s);
  const codes = [];
  s = s.replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+|#[^)\s]*)\)/g, '<a href="$2" rel="noopener noreferrer">$1</a>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${codes[i]}</code>`);
}
const cells = (line) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());

export function renderMarkdown(md) {
  const lines = md.replace(/\r/g, "").split("\n");
  const out = [], toc = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) {                       // fenced block: examples
      const buf = []; i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++; out.push(`<pre>${esc(buf.join("\n"))}</pre>`); continue;
    }
    if (/^<\/?details>\s*$/.test(line.trim())) { out.push(line.trim()); i++; continue; }
    const sm = line.trim().match(/^<summary>(.*)<\/summary>$/);
    if (sm) { out.push(`<summary>${inline(sm[1])}</summary>`); i++; continue; }
    const hm = line.match(/^(#{1,4})\s+(.*)$/);
    if (hm) {
      const n = hm[1].length, id = slug(hm[2]);
      if (n === 2 || n === 3) toc.push({ level: n, id, text: hm[2].replace(/[*`]/g, "") });
      out.push(`<h${n} id="${id}">${inline(hm[2])}</h${n}>`); i++; continue;
    }
    if (/^---+\s*$/.test(line)) { out.push("<hr>"); i++; continue; }
    if (/^\|/.test(line) && i + 1 < lines.length && /^\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const head = cells(line); i += 2; const rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) rows.push(cells(lines[i++]));
      const empty = head.every((c) => !c);
      out.push("<div class='scroll'><table>" + (empty ? "" : "<thead><tr>" + head.map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead>") +
        "<tbody>" + rows.map((r) => "<tr>" + r.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>").join("") + "</tbody></table></div>");
      continue;
    }
    if (/^>\s?/.test(line)) {
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, ""));
      out.push(`<blockquote>${buf.map(inline).join("<br>")}</blockquote>`); continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\./.test(line), items = [];
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) items.push(inline(lines[i++].replace(/^\s*([-*]|\d+\.)\s+/, "")));
      const tag = ordered ? "ol" : "ul"; out.push(`<${tag}>${items.map((x) => `<li>${x}</li>`).join("")}</${tag}>`); continue;
    }
    if (!line.trim()) { i++; continue; }
    const buf = [];
    while (i < lines.length && lines[i].trim() && !/^(```|#{1,4}\s|\||>|---|<\/?details|<summary|\s*([-*]|\d+\.)\s)/.test(lines[i])) buf.push(lines[i++]);
    if (!buf.length) { buf.push(lines[i++]); }
    out.push(`<p>${buf.map(inline).join(" ")}</p>`);
  }
  return { html: out.join("\n"), toc };
}
