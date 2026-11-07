import json
data = json.load(open("/home/claude/geom/letters.json"))
html = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Devanagari stroke geometry</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#faf8f4;--ink:#1d1d1f;--mute:#6b6b70;--line:#e3dfd6;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#18181a;--ink:#ececec;--mute:#9a9aa0;--line:#2f2f33;--card:#202023}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 Inter,system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:20px 14px 60px}h1{font-size:22px;margin:0 0 4px}
p.lede{color:var(--mute);margin:0 0 12px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 14px}
.chip{border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:999px;padding:4px 10px;font:inherit;font-size:13px;cursor:pointer}
.chip.on{background:var(--ink);color:var(--bg)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.cell{cursor:pointer;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:6px 8px 8px}
.hd{display:flex;justify-content:space-between;align-items:baseline;font-size:13px}
.hd .ref{font-family:"Noto Sans Devanagari",sans-serif;font-size:22px;color:var(--mute)}
svg{width:100%;height:auto;display:block}
.body{stroke:#2f7fd1}.second{stroke:#3f9a3a}.struct{stroke:#7d4a9e}.accent{stroke:#e08a2c}
path{fill:none;stroke-width:3.2;stroke-linecap:round;stroke-linejoin:round}
.mono path{stroke:var(--ink)!important}
.j-red{fill:#c9372c}.j-touch{fill:none;stroke:#e08a2c;stroke-width:1.6}.j-cross{stroke:#e08a2c;stroke-width:1.6}
.hidej .jn{display:none}
.var{font-size:11px;color:var(--mute)}
textarea{width:100%;height:160px;font:12px ui-monospace,monospace;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px}
.note{color:var(--mute);font-size:12.5px}
</style></head><body><main>
<h1>Devanagari stroke geometry</h1>
<p class="note" style="margin:0 0 6px"><b>Checkpoint v1.1</b> · stroke graph · 2 Nov 2026</p>
<p class="lede">Each letter traced from your drawings as proportional paths in a 100 × 100 box, with the headline at y = 20. The colors and junction marks follow your sheet. The shapes are approximate; the structure matches the stroke table.</p>
<div class="chips">
<button class="chip on" id="bColor">Colors</button><button class="chip" id="bMono">Plain ink</button>
<button class="chip on" id="bJ">Junction marks</button>
</div>
<p class="note">Tap a letter to see its proportional description.</p>
<div id="det" style="display:none;border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:14px;background:var(--card)"></div>
<div class="grid" id="g"></div>
<h2 style="font-size:16px;margin-top:28px">Data</h2>
<p class="note">Roles: body = blue main form, second = green form, struct = purple headline and connectors, accent = orange. Junctions: red = between forms or with the headline, touch = ○, cross = ×. Paths are SVG path syntax. Every stroke has an id, and every junction lists the strokes it joins, where along each one it sits, and how many branches meet there. Each letter also has a "frame" record (headline extent, stems, bounding box). Grammatical marks are orange accents with a "function" tag. Each letter also has a "structure" list (positions as percentages: across = along the top bar, down = from the bar to the baseline) and a plain-English "description" derived from it.</p>
<textarea id="json" readonly></textarea>
<div class="chips"><button class="chip" id="copy">Copy JSON</button></div>
</main>
<script>
const D=__DATA__;
const g=document.getElementById("g");
function svg(r){let s='<svg viewBox="0 0 100 100">';
r.strokes.forEach(k=>s+=`<path class="${k.role}" d="${k.d}"/>`);
s+='<g class="jn">';r.junctions.forEach(j=>{
 if(j.t==="red")s+=`<circle class="j-red" cx="${j.x}" cy="${j.y}" r="2.6"/>`;
 else if(j.t==="touch")s+=`<circle class="j-touch" cx="${j.x}" cy="${j.y}" r="4.6"/>`;
 else s+=`<path class="j-cross" d="M${j.x-4.5} ${j.y-4.5} L${j.x+4.5} ${j.y+4.5} M${j.x+4.5} ${j.y-4.5} L${j.x-4.5} ${j.y+4.5}" style="stroke:#e08a2c;stroke-width:1.6"/>`;});
return s+'</g></svg>'}
g.innerHTML=D.map(r=>`<div class="cell"><div class="hd"><span>${r.iast}${r.variant?` <span class="var">${r.variant}</span>`:""}</span><span class="ref">${r.glyph}</span></div>${svg(r)}</div>`).join("");
g.querySelectorAll(".cell").forEach((c,i)=>c.onclick=()=>{const r=D[i],d=document.getElementById("det");d.style.display="block";
d.innerHTML=`<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start"><div style="width:180px">${svg(r)}</div><div style="flex:1;min-width:240px"><div style="font-weight:600;margin-bottom:6px"><span class="ref" style="font-family:'Noto Sans Devanagari';font-size:26px">${r.glyph}</span> ${r.iast}${r.variant?" ("+r.variant+")":""}</div><div>${r.description}</div>
<table style="margin-top:10px;font-size:12.5px;border-collapse:collapse;width:100%"><tr><th style="text-align:left">Junction</th><th style="text-align:left">Type</th><th style="text-align:left">Branches</th><th style="text-align:left">Strokes joined (position along stroke)</th></tr>
${r.junctions.map(j=>`<tr><td>${j.id}</td><td>${{red:"red dot",touch:"○ touch",cross:"× cross"}[j.t]}</td><td>${j.branches}</td><td>${j.members.map(m=>{const s=r.strokes.find(x=>x.id===m.stroke);return `${m.stroke} ${s.role==="body"?"blue":s.role==="second"?"green":s.role==="struct"?"purple":"orange"} ${m.where==="middle"?Math.round(m.at*100)+"% along":m.where}`}).join("; ")}</td></tr>`).join("")}</table></div></div>`;d.scrollIntoView({behavior:"smooth",block:"nearest"})});
document.getElementById("json").value=JSON.stringify(D,null,1);
const tog=(id,fn)=>document.getElementById(id).onclick=fn;
tog("bColor",()=>{g.classList.remove("mono");bColor.classList.add("on");bMono.classList.remove("on")});
tog("bMono",()=>{g.classList.add("mono");bMono.classList.add("on");bColor.classList.remove("on")});
tog("bJ",()=>{g.classList.toggle("hidej");bJ.classList.toggle("on")});
tog("copy",async()=>{try{await navigator.clipboard.writeText(document.getElementById("json").value);copy.textContent="Copied"}catch(e){copy.textContent="Select the text above to copy"}});
</script></body></html>"""
open("/home/claude/geom/index.html", "w").write(html.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
