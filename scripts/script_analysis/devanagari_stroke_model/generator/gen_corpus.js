// Offline corpus builder: runs the unchanged gen2.js (Generator v2) over many style configs, with the same filters as the
// page's run(): reject copies of real letters (REAL_KEYS / chamfer < 2.0) and near-duplicates (3.0 same frame, 2.2 other).
// usage: node gen_corpus.js <styles> <seed> > corpus.json
const fs = require("fs"), vm = require("vm"), path = require("path");
const src = fs.readFileSync(path.join(__dirname, "gen2.js"), "utf8");
const REAL = JSON.parse(fs.readFileSync(path.join(__dirname, "real_pts.json"), "utf8"));
const ctx = { Math, console, JSON, Object, Array, Set, document: null };
vm.createContext(ctx);
vm.runInContext(src + `
function ptsOf(o){let out=[];for(const k of o.s){const toks=k.d.match(/[MHVLCQ]|-?\\d+\\.?\\d*/g);let cmd,cur=[0,0],i=0;const num=()=>+toks[i++];const seg=(fn)=>{for(let t=1;t<=24;t++)out.push(fn(t/24))};
 while(i<toks.length){if(/[A-Z]/.test(toks[i])){cmd=toks[i++];}
  if(cmd==="M"){cur=[num(),num()];out.push(cur)}else if(cmd==="H"){const x=num(),c=cur;seg(t=>[c[0]+(x-c[0])*t,c[1]]);cur=[x,c[1]]}else if(cmd==="V"){const y=num(),c=cur;seg(t=>[c[0],c[1]+(y-c[1])*t]);cur=[c[0],y]}
  else if(cmd==="L"){const p=[num(),num()],c=cur;seg(t=>[c[0]+(p[0]-c[0])*t,c[1]+(p[1]-c[1])*t]);cur=p}
  else if(cmd==="Q"){const a=[num(),num()],p=[num(),num()],c=cur;seg(t=>[0,1].map(j=>(1-t)*(1-t)*c[j]+2*(1-t)*t*a[j]+t*t*p[j]));cur=p}
  else if(cmd==="C"){const a=[num(),num()],b=[num(),num()],p=[num(),num()],c=cur;seg(t=>cub(c,a,b,p,t));cur=p}}}
 return out}
function setSeed(s){R=mul(s)}
function build(nStyles, seed){
  const sections=Object.keys(DEV_CONFIG), styles=[];
  for(let si=0;si<nStyles;si++){
    R=mul(seed*7919+si); const cfg={},mut=[];
    for(const k of sections){ if(si>0&&C(.5)){cfg[k]=MUTATE[k](DEV_CONFIG[k]);mut.push(k)} else cfg[k]=DEV_CONFIG[k] }
    R=mul(seed*104729+si*31+1);
    const seen=new Set(),SET=[],pts=[];let tries=0;
    while(SET.length<30&&tries<4000){tries++;const o=letter(cfg);const key=JSON.stringify(o.sig);if(seen.has(key))continue;
      if(REAL_KEYS[o.key]){seen.add(key);continue}
      const nA=SET.filter(x=>x.acc).length;if(o.acc&&nA>=Math.max(2,Math.round(30*cfg.accents.prob*1.4)))continue;
      const noBar=o2=>!o2.s.some(s=>/^M[\\d.]+ 20 H/.test(s.d)),isG=o2=>o2.s.some(s=>s.role==="second");
      if(noBar(o)&&SET.filter(noBar).length>=Math.ceil(30*(1-cfg.frame.barProb)*1.3))continue;
      if(isG(o)&&SET.filter(isG).length>=15)continue;
      const A=ptsOf(o);let best=1e9;for(const g in REAL_PTS){const d=chamfer(A,REAL_PTS[g],Math.min(best,6));if(d<best)best=d}
      if(best<2.0)continue;
      let close=false;const fr=o.key.split("|").slice(0,2).join("|");
      for(let q=0;q<pts.length;q++){const lim=SET[q].key.split("|").slice(0,2).join("|")===fr?3.0:2.2;if(chamfer(A,pts[q],lim)<lim){close=true;break}}
      if(close)continue;
      seen.add(key);SET.push(o);pts.push(A)}
    styles.push({id:si,mutated:mut,letters:SET.map(o=>({s:o.s,j:o.j,key:o.key,anchors:o.anchors,r:o.r,acc:o.acc?1:0}))});
  }
  return styles}
`, ctx);
ctx.REAL_PTS = REAL;
const n = +process.argv[2] || 40, seed = +process.argv[3] || 1;
process.stdout.write(JSON.stringify({version: 1, source: "gen2.js (Generator v2)", box: {w: 100, h: 100, top: 20, base: 88}, styles: vm.runInContext(`build(${n},${seed})`, ctx)}));
