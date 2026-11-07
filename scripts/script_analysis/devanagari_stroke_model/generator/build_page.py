import json
real = json.load(open('real_pts.json'))
js = open('gen2.js').read()
html = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Generated Devanagari-like script</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#faf8f4;--ink:#1d1d1f;--mute:#6b6b70;--line:#e3dfd6;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#18181a;--ink:#ececec;--mute:#9a9aa0;--line:#2f2f33;--card:#202023}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 Inter,system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:20px 14px 60px}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:24px 0 8px}
p.lede{color:var(--mute);margin:0 0 12px}.note{color:var(--mute);font-size:12.5px}.dev{font-family:"Noto Sans Devanagari",sans-serif}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 12px;align-items:center}
.chip{border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:999px;padding:4px 10px;font:inherit;font-size:13px;cursor:pointer}
.chip.on{background:var(--ink);color:var(--bg)}
input[type=number]{font:inherit;font-size:13px;width:90px;padding:4px 8px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink)}
.cfgs{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.cfg{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:var(--card)}
.cfg.mut{outline:2px solid #e08a2c}
.cfg pre{font:11.5px/1.4 ui-monospace,monospace;white-space:pre-wrap;margin:6px 0 0;color:var(--mute)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px}
.cell{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:6px 8px 8px;cursor:pointer}
.cell.sel{outline:2px solid #2f7fd1}
.hd{font-size:12px;color:var(--mute)}
svg{width:100%;height:auto;display:block}
path{fill:none;stroke-width:3.2;stroke-linecap:round;stroke-linejoin:round}
.body{stroke:#2f7fd1}.second{stroke:#3f9a3a}.struct{stroke:#7d4a9e}.accent{stroke:#e08a2c}
.mono path.body,.mono path.second,.mono path.struct,.mono path.accent{stroke:var(--ink)}
.hidej .jn{display:none}
#det{display:none;border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:14px;background:var(--card)}
#det ul{margin:6px 0 0;padding-left:18px}
table{border-collapse:collapse;font-size:13.5px;width:100%;max-width:560px}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}td.n{text-align:right;font-variant-numeric:tabular-nums}
</style></head><body><main>
<h1>Generated Devanagari-like script</h1>
<p class="note" style="margin:0 0 6px"><b>Generator v2</b> · five style configs · built on Checkpoint v1.1</p>
<p class="lede">New letters built from five style configs. Each config starts from Devanagari's statistics and can be mutated on its own. Letters too close to a real Devanagari letter, or to each other, are rejected.</p>
<h2>Style</h2>
<div class="cfgs" id="cfgs"></div>
<div class="chips" style="margin-top:10px"><button class="chip" id="allDev">All Devanagari</button><button class="chip" id="allMut">Mutate all</button></div>
<h2>Letters</h2>
<div class="chips">
<span class="note">Seed</span><input id="seed" type="number" value="7">
<button class="chip" id="gen">Generate</button><button class="chip" id="rnd">New random set</button>
<button class="chip" id="bReal">Allow resemblance to real letters</button>
</div>
<div class="chips">
<button class="chip on" id="bColor">Colors</button><button class="chip" id="bMono">Plain ink</button>
<button class="chip on" id="bJ">Junction marks</button>
</div>
<p class="note" id="status"></p>
<div id="det"></div>
<div class="grid" id="g"></div>
<h2>How it compares with Devanagari</h2>
<table id="stats"></table>
<p class="note" style="margin-top:8px">Similarity is measured by comparing the points along every stroke of two letters in place. A letter counts as a copy of a real letter if its recipe (bar, right side, body type and variant, extras) matches that letter (adding or removing the top bar, or the full-height stem, is enough to make a new letter), or if its strokes sit within 2.0 units of it on average (in a 100-unit box). Letters within 2.2 units of another generated letter are rejected as duplicates, and within 3.0 units if both have the same frame (same bar and right side), since letters sharing a frame need bigger differences in their bodies to stand apart.</p>
</main>
<script>
const REAL=__REAL__;
__JS__
const DEV={"bar":0.85,"green":0.45,"accent":0.085,"cross":0.19,"red":1.6,"touch":1.3};
const STYLE={};for(const k in DEV_CONFIG)STYLE[k]={mode:"dev",value:null};
let allowReal=false,SET=[];
const $=id=>document.getElementById(id);
function cfgNow(){const c={};for(const k in DEV_CONFIG)c[k]=STYLE[k].mode==="mut"?STYLE[k].value:DEV_CONFIG[k];return c}
function drawCfgs(){$("cfgs").innerHTML=Object.keys(DEV_CONFIG).map(k=>{const st=STYLE[k],v=st.mode==="mut"?st.value:DEV_CONFIG[k];
 return `<div class="cfg ${st.mode==="mut"?"mut":""}"><b>${SECTION_INFO[k][0]}</b> <span class="note">· ${st.mode==="mut"?"mutated":"Devanagari"}</span><div class="note">${SECTION_INFO[k][1]}</div>
 <div class="chips" style="margin:6px 0 0"><button class="chip ${st.mode==="dev"?"on":""}" data-k="${k}" data-a="dev">Devanagari</button><button class="chip ${st.mode==="mut"?"on":""}" data-k="${k}" data-a="mut">Mutate</button></div>
 <pre>${JSON.stringify(v,null,1).replace(/\n\s*/g," ").replace(/^\{ | \}$/g,"")}</pre></div>`}).join("");
 $("cfgs").querySelectorAll("button").forEach(b=>b.onclick=()=>{const k=b.dataset.k;if(b.dataset.a==="dev")STYLE[k].mode="dev";else{R=mul(Math.floor(Math.random()*1e9));STYLE[k]={mode:"mut",value:MUTATE[k](DEV_CONFIG[k])}}drawCfgs();run(+$("seed").value||1)})}
function svg(o){let s='<svg viewBox="0 -6 100 106">';o.s.forEach(k=>s+=`<path class="${k.role}" d="${k.d}"/>`);s+='<g class="jn">';
 o.j.forEach(j=>{if(j.t==="red")s+=`<circle cx="${j.x}" cy="${j.y}" r="2.6" fill="#c9372c"/>`;else if(j.t==="touch")s+=`<circle cx="${j.x}" cy="${j.y}" r="4.6" fill="none" stroke="#e08a2c" stroke-width="1.6"/>`;
 else s+=`<path d="M${j.x-4.5} ${j.y-4.5} L${j.x+4.5} ${j.y+4.5} M${j.x+4.5} ${j.y-4.5} L${j.x-4.5} ${j.y+4.5}" style="stroke:#e08a2c;stroke-width:1.6"/>`});return s+'</g></svg>'}
function run(seed){const cfg=cfgNow();R=mul(seed);const seen=new Set();SET=[];let tries=0,rejReal=0,rejGen=0;const pts=[];
 while(SET.length<30&&tries<4000){tries++;const o=letter(cfg);const key=JSON.stringify(o.sig);if(seen.has(key))continue;
  o.copyOf=REAL_KEYS[o.key];
  if(!allowReal&&o.copyOf){rejReal++;seen.add(key);continue}
  const nA=SET.filter(x=>x.acc).length;if(o.acc&&nA>=Math.max(2,Math.round(30*cfg.accents.prob*1.4)))continue;const noBar=o2=>!o2.s.some(s=>/^M[\d.]+ 20 H/.test(s.d)),isG=o2=>o2.s.some(s=>s.role==="second");if(noBar(o)&&SET.filter(noBar).length>=Math.ceil(30*(1-cfg.frame.barProb)*1.3))continue;if(isG(o)&&SET.filter(isG).length>=Math.ceil(30*0.5))continue;
  const A=ptsOf(o);let best=[1e9,""];for(const g in REAL){const d=chamfer(A,REAL[g],Math.min(best[0],6));if(d<best[0])best=[d,g]}
  o.near=best;if(!allowReal&&best[0]<2.0){rejReal++;continue}
  let tooClose=false;const fr=o.key.split("|").slice(0,2).join("|");for(let q=0;q<pts.length;q++){const lim=SET[q].key.split("|").slice(0,2).join("|")===fr?3.0:2.2;if(chamfer(A,pts[q],lim)<lim){tooClose=true;break}}if(tooClose){rejGen++;continue}
  seen.add(key);SET.push(o);pts.push(A)}
 $("status").textContent=`${SET.length} letters · rejected ${rejReal} too close to a real letter and ${rejGen} too close to another generated letter.`;
 const g=$("g");g.innerHTML=SET.map((o,i)=>`<div class="cell"><div class="hd">G${i+1}</div>${svg(o)}</div>`).join("");
 g.querySelectorAll(".cell").forEach((c,i)=>c.onclick=()=>{g.querySelectorAll(".cell").forEach(x=>x.classList.remove("sel"));c.classList.add("sel");const d=$("det");d.style.display="block";const o=SET[i];
  d.innerHTML=`<div style="display:flex;gap:14px;flex-wrap:wrap"><div style="width:170px">${svg(o)}</div><div style="flex:1;min-width:220px"><b>G${i+1}</b><ul>${o.r.map(x=>`<li>${x}</li>`).join("")}</ul><p class="note" style="margin:8px 0 0">${o.copyOf?`Same recipe as real <span class="dev" style="font-size:18px">${o.copyOf}</span> (allowed because resemblance is on). `:""}Closest real letter by shape: <span class="dev" style="font-size:18px">${o.near[1]}</span> (distance ${o.near[0].toFixed(1)})</p></div></div>`;d.scrollIntoView({behavior:"smooth",block:"nearest"})});
 $("det").style.display="none";
 const n=SET.length||1,st={bar:SET.filter(o=>o.s.some(s=>s.role==="struct"&&/ H/.test(s.d)&&/^M[\d.]+ 20 H/.test(s.d))).length/n,green:SET.filter(o=>o.s.some(s=>s.role==="second")).length/n,
  accent:SET.filter(o=>o.acc).length/n,cross:SET.filter(o=>o.j.some(j=>j.t==="cross")).length/n,red:SET.reduce((a,o)=>a+o.j.filter(j=>j.t==="red").length,0)/n,touch:SET.reduce((a,o)=>a+o.j.filter(j=>j.t==="touch").length,0)/n};
 const rows=[["Letters with a top bar","bar",1],["Letters with a green form","green",1],["Letters with an accent","accent",1],["Letters with a self-crossing","cross",1],["Red dots per letter","red",0],["Touches (○) per letter","touch",0]];
 $("stats").innerHTML=`<tr><th></th><th>Devanagari</th><th>This set</th></tr>`+rows.map(([l,k,p])=>`<tr><td>${l}</td><td class="n">${p?Math.round(DEV[k]*100)+"%":DEV[k].toFixed(1)}</td><td class="n">${p?Math.round(st[k]*100)+"%":st[k].toFixed(1)}</td></tr>`).join("")}
$("gen").onclick=()=>run(+$("seed").value||1);$("rnd").onclick=()=>{$("seed").value=Math.floor(Math.random()*99999);run(+$("seed").value)};
$("bReal").onclick=()=>{allowReal=!allowReal;$("bReal").classList.toggle("on",allowReal);run(+$("seed").value||1)};
$("allDev").onclick=()=>{for(const k in STYLE)STYLE[k].mode="dev";drawCfgs();run(+$("seed").value||1)};
$("allMut").onclick=()=>{R=mul(Math.floor(Math.random()*1e9));for(const k in STYLE)STYLE[k]={mode:"mut",value:MUTATE[k](DEV_CONFIG[k])};drawCfgs();run(+$("seed").value||1)};
$("bColor").onclick=()=>{$("g").classList.remove("mono");$("det").classList.remove("mono");bColor.classList.add("on");bMono.classList.remove("on")};
$("bMono").onclick=()=>{$("g").classList.add("mono");$("det").classList.add("mono");bMono.classList.add("on");bColor.classList.remove("on")};
$("bJ").onclick=()=>{$("g").classList.toggle("hidej");$("det").classList.toggle("hidej");bJ.classList.toggle("on")};
drawCfgs();run(7);
</script></body></html>'''
open('index.html','w').write(html.replace('__REAL__', json.dumps(real, separators=(',',':'))).replace('__JS__', js))
