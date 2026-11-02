// ===== Generator v2: five configs + similarity check =====
const DEV_CONFIG = {
  frame: { barProb: 0.85, stem: { blue: 0.40, none: 0.40, green: 0.11, gamma: 0.09 }, stemX: [64, 74], barFrom: [14, 20], barTo: [84, 90], bottom: [80, 88] },
  bodies: { weights: { hang: 11, cup: 6, hook: 6, loop: 4, U: 4, rev3: 4, lobes: 3, cross: 2, corner: 1 } },
  attach: { toBlueStem: "touch", toGreenStem: "red", toBar: "red", descenderToBar: "touch", descenderToBody: "red", diagonalProb: 0.35, stemTailProb: 0.1, cornerTailProb: 0.3 },
  accents: { prob: 0.09, types: { "1L": 0.5, "1R": 0.25, "2L": 0.25, "2R": 0 }, height: [12, 16], curl: [6, 12] },
  anchors: { where: "rightmost" }
};
const SECTION_INFO = {
  frame: ["Frame", "Top bar, the right-hand stem type, and overall proportions."],
  bodies: ["Body shapes", "Which blue body types appear, and how often."],
  attach: ["Attachments", "How forms join: touch (○) or red dot, plus how often diagonals and tails are added."],
  accents: ["Accent shapes", "How often accents appear, which of the four types, and their size."],
  anchors: ["Accent anchors", "Which point where a line meets the bar from below takes the accent."]
};
let R; const U = (a, b) => a + (b - a) * R(), C = p => R() < p, f = n => Math.round(n * 10) / 10;
const P = a => a[Math.floor(R() * a.length)];
const W = obj => { const e = Object.entries(obj).filter(([, w]) => w > 0); const t = e.reduce((a, [, w]) => a + w, 0); let r = R() * t; for (const [k, w] of e) { if ((r -= w) < 0) return k } return e[e.length - 1][0] };
function mul(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296 } }
function cub(p0, p1, p2, p3, t) { const m = 1 - t; return [0, 1].map(i => m * m * m * p0[i] + 3 * m * m * t * p1[i] + 3 * m * t * t * p2[i] + t * t * t * p3[i]) }
function tf(d, ax, ay, sx, sy, ox, oy) { const tk = d.match(/[MHVLCQ]|-?\d+\.?\d*/g); let out = [], cmd, k = 0; for (const t of tk) { if (/[A-Z]/.test(t)) { cmd = t; k = 0; out.push(t); continue } const v = +t; let r; if (cmd === "H") r = ox + (v - ax) * sx; else if (cmd === "V") r = oy + (v - ay) * sy; else r = (k % 2 === 0) ? ox + (v - ax) * sx : oy + (v - ay) * sy; k++; out.push(f(r)) } return out.join(" ") }
const tp = (x, y, ax, ay, sx, sy, ox, oy) => [f(ox + (x - ax) * sx), f(oy + (y - ay) * sy)];
const HANG = {
  "open hook": { a: [50, 32], d: "M50 32 C32 30 28 48 34 60 C40 72 60 72 70 64", x: [], t: [] },
  "closed loop": { a: [52, 32], d: "M52 32 C34 32 30 60 44 68 C58 74 72 58 64 42 C60 34 56 32 52 32", x: [], t: [] },
  "S-hook": { a: [56, 32], d: "M56 32 C38 30 30 40 42 46 C66 52 68 72 48 76 C34 78 26 72 30 64", x: [], t: [] },
  "S-hook with crossed tail": { a: [56, 32], d: "M56 32 C38 30 30 40 42 46 C66 54 66 74 50 78 C40 81 30 82 24 76 C20 70 30 66 40 84", x: [[31, 77]], t: [] },
  "loop with inner curl": { a: [58, 32], d: "M58 32 C40 30 34 48 38 62 C42 80 66 80 64 66 C62 56 50 58 50 66 C50 70 52 74 56.9 75.8", x: [], t: [[56.9, 75.8]] },
  "hook with crossed curl": { a: [52, 34], d: "M52 34 C36 34 30 50 36 60 C42 70 56 74 62 70 C66 66 60 62 54 66 C48 70 50 80 56 86", x: [[53, 69]], t: [] },
  "arc with two lower arcs": { a: [63, 43], d: ["M63 43 C58 36 46 30 36 31 C28 32 26 42 35 53", "M35 53 C44 50 56 52 62 56 C66 60 62 66 54 68", "M35 53 C28 60 28 76 36 84 C44 90 56 90 64 88"], x: [], t: [[35, 53]] }
};
const ATTACHING = ["cup", "hook", "loop", "U", "rev3", "lobes", "cross"];   // bodies that join the right-hand stem
const FREE = ["hang", "U", "hook", "corner"];                                 // bodies that stand apart from it
let HAS_BAR = true;
function letter(cfg) {
  const o = { s: [], j: [], r: [], sig: [], anchors: [] }; const BAR_Y = 20, GAP = 7;     // GAP: white space kept between a body curve and the bar, about 0.6 of a short descender (10-14 high)
  // A body stroke keeps clear of the headline: every control point and every interior end point of a body or second stroke stays at
  // least GAP below the bar (the curve "rises less"), except where a stroke meets the bar on purpose (an end point exactly on it).
  // A Bezier stays inside its control points, so the curve cannot come closer. Straight stems and the flag of a green Г are left alone.
  const RISE = 4;       // a curve that leaves a descender's lower end (or any start below the bar) rises at most this far in its first segment
  const clampTop = d => { if (!/[CQ]/.test(d)) return d; const tk = d.match(/[MHVLCQ]|-?\d+\.?\d*/g); let cmd, k = 0; const nums = tk.filter(t => !/[A-Z]/.test(t)).length, lastY = nums - 1; let seen = 0, startY = null, firstSeg = true, segs = 0;
    return tk.map(t => { if (/[A-Z]/.test(t)) { cmd = t; k = 0; return t } const v = +t, pi = Math.floor(k / 2), isY = k % 2 === 1, isLast = seen === lastY; k++; seen++; if (!isY) return t; if (cmd === "M") { if (startY === null) startY = v; return t } if (cmd === "H") return t;
      const onBar = Math.abs(v - BAR_Y) <= 0.01 && isLast;                  // only the very last end point may rest on the bar
      if (cmd === "V") return (v < BAR_Y + GAP && !onBar) ? f(BAR_Y + GAP) : t;
      const ctrl = (cmd === "C" && pi % 3 < 2) || (cmd === "Q" && pi % 2 === 0);
      let lo = BAR_Y + GAP; if (ctrl && firstSeg && startY > BAR_Y + 0.5) lo = Math.max(lo, startY - RISE);
      if ((cmd === "C" && pi % 3 === 2) || (cmd === "Q" && pi % 2 === 1)) { if (firstSeg) firstSeg = false }
      return (v < lo && (ctrl || !onBar)) ? f(lo) : t }).join(" ") }
  const A = (role, d) => o.s.push({ role, d: (HAS_BAR && (role === "body" || role === "second")) ? clampTop(d) : d }), J = (t, x, y) => o.j.push({ t, x: f(x), y: f(y) });
  const F = cfg.frame, AT = cfg.attach;
  const hasBar = C(F.barProb); HAS_BAR = hasBar; let stem = W(F.stem);
  if (!hasBar && (stem === "green" || stem === "none")) stem = C(0.5) ? "gamma" : "blue";
  if (hasBar && stem === "gamma") stem = "green";
  const S = f(U(...F.stemX)), bot = f(U(...F.bottom)), bx0 = f(U(...F.barFrom)), bx1 = f(U(...F.barTo));
  if (hasBar) A("struct", `M${bx0} 20 H${bx1}`);
  const jt = stem === "blue" ? AT.toBlueStem : AT.toGreenStem;
  if (stem === "blue") { A("body", `M${S} 20 V${bot}`); if (hasBar) { J(AT.toBar, S, 20); o.anchors.push(S) } o.r.push(`Frame: blue stem at ${Math.round((S - bx0) / (bx1 - bx0) * 100)}% across${hasBar ? "" : ", no bar"}.`) }
  if (stem === "green") { A("second", `M${S} 20 V${bot}`); J(AT.toBar, S, 20); o.anchors.push(S); o.r.push("Frame: separate green stem on the right.") }
  if (stem === "gamma") { const fl = f(U(12, 18)); A("second", `M${S} ${bot} V22`); A("second", `M${S} 22 H${f(S + fl)}`); J("touch", S, 22); o.r.push("Frame: green Г on the right (stem plus touching flag), no bar.") }
  if (stem === "none") o.r.push("Frame: bar only, no stem.");
  o.sig.push(hasBar, stem);
  // body choice, restricted to what fits the frame
  const allowed = (stem === "blue" || stem === "gamma") ? ATTACHING : FREE;
  const w = {}; for (const k of allowed) w[k] = cfg.bodies.weights[k] || 0;
  if (!hasBar) { delete w.hang; delete w.U; delete w.corner; delete w.rev3; delete w.lobes }
  if (Object.values(w).every(v => !v)) w[allowed.includes("cup") ? "cup" : "hook"] = 1;
  const body = W(w); o.sig.push(body);
  let diag = null; const J2 = jt;
  if (body === "loop") {
    const y1 = f(U(30, 40)), y2 = f(y1 + U(16, 24)), wd = U(20, 30), c1 = [S - wd * 1.25, y1 - 6], c2 = [S - wd * 1.25, y2 + 8];
    A("body", `M${S} ${y1} C${f(c1[0])} ${f(c1[1])} ${f(c2[0])} ${f(c2[1])} ${S} ${y2}`); J(J2, S, y1); J(J2, S, y2);
    if (C(.3)) { const m = cub([S, y1], c1, c2, [S, y2], .5), ix = m[0] + 5, iy = m[1]; A("body", `M${f(m[0])} ${f(m[1])} C${f(ix + 4)} ${f(iy - 7)} ${f(ix + 10)} ${f(iy + 2)} ${f(ix + 3)} ${f(iy + 4)}`); J("touch", m[0], m[1]); o.sub = "curl"; o.r.push("A small blue curl sits inside the loop, touching it (○).") }
    diag = { p: cub([S, y1], c1, c2, [S, y2], .3), q: [S, y2] }; o.r.push(`Body: blue loop leaving the stem and returning to it (${Math.round((y1 - 20) / 68 * 100)}%–${Math.round((y2 - 20) / 68 * 100)}% down).`)
  }
  if (body === "cup") {
    const cx = U(22, 34), cy = U(44, 60), ys = U(38, 56); let start;
    const cs = hasBar ? W({ frombar: .45, hook: .35, fromdesc: .2 }) : "hook";
    if (cs === "fromdesc") { const x0 = U(30, 42), yd = U(30, 34); A("struct", `M${f(x0)} 20 V${f(yd)}`); J(cfg.attach.descenderToBar, x0, 20); J(cfg.attach.descenderToBody, x0, yd); o.anchors.push(x0);
      start = `M${f(x0)} ${f(yd)} C${f(x0 - 14)} ${f(yd)} ${f(cx - 16)} ${f(cy - 8)} ${f(cx)} ${f(cy)}`; o.r.push("Body: short purple descender holds a blue cup that turns at a corner (○)."); o.sub = "fromdesc" }
    else if (cs === "frombar") { const x0 = U(28, 42); start = `M${f(x0)} 20 C${f(x0 + U(2, 8))} 32 ${f(cx - U(12, 18))} ${f(cy - U(4, 12))} ${f(cx)} ${f(cy)}`; J(AT.toBar, x0, 20); o.anchors.push(x0); o.r.push("Body: blue cup drops from the bar and turns at a corner (○)."); o.sub = "frombar" }
    else { const sx = U(20, 30), sy = hasBar ? U(34, 38) : U(25, 32); start = `M${f(sx)} ${f(sy)} C${f(sx - 5)} ${f(sy - 9)} ${f(sx + 11)} ${f(sy - 11)} ${f(sx + 13)} ${f(sy - 1)} C${f(sx + 14)} ${f(sy + 9)} ${f(cx + 6)} ${f(cy - 10)} ${f(cx)} ${f(cy)}`; o.r.push("Body: blue hooked stroke curls over and comes down to a corner (○)."); o.sub = "hook" }
    A("body", start); J("touch", cx, cy); const sag = U(0, 12);
    A("body", `M${f(cx)} ${f(cy)} C${f(cx + 12)} ${f(cy + sag)} ${f(S - 12)} ${f(ys + sag)} ${S} ${f(ys)}`); J(J2, S, ys);
    o.r.push(`Connector from the corner to the stem${sag > 6 ? ", sagging" : ""}.`);
    if (C(AT.cornerTailProb)) { A("body", `M${f(cx)} ${f(cy)} C${f(cx + 3)} ${f(cy + 12)} ${f(cx + 10)} ${f(cy + 20)} ${f(cx + 20)} ${f(cy + 26)}`); o.r.push("A tail leaves the same corner: three strokes meet at one ○."); o.sig.push("tail3") }
  }
  if (body === "hook") {
    if (stem === "blue" || stem === "gamma") {
      const ys = U(38, 54);
      const hv = W({ in: .4, out: .4, through: .2 });
      if (hv === "through") { const sx = U(24, 34), sy = ys + U(6, 14), ex = S + U(10, 16), ey = ys - U(4, 10); A("body", `M${f(sx)} ${f(sy)} C${f(sx + 10)} ${f(ys + 2)} ${f(S - 8)} ${f(ys)} ${S} ${f(ys)} C${f(S + 5)} ${f(ys)} ${f(ex - 4)} ${f(ey + 2)} ${f(ex)} ${f(ey)}`); J("cross", S, ys); o.sub = "through"; o.sig.push("through"); o.r.push("Body: blue stroke sweeps up through the stem, crossing it (×).") }
      else if (hv === "in") { const sx = U(26, 36), sy = ys + U(-1.5, 1.5); A("body", `M${f(sx)} ${f(sy)} C${f(sx + 4)} ${f(ys - 12)} ${f(S - 14)} ${f(ys - 12)} ${S} ${f(ys)}`); o.r.push("Body: blue hook arches over and lands on the stem.") }
      else { const ex = U(28, 38), ey = ys + U(30, 40); A("body", `M${S} ${f(ys)} C${f(S - 16)} ${f(ys - 6)} ${f(ex)} ${f(ys)} ${f(ex)} ${f(ey)}`); o.r.push("Body: blue curve leaves the stem and drops to the left.") }
      if (hv !== "through") { J(J2, S, ys); o.sub = hv; o.sig.push(o.sub) }
    } else {
      const x0 = U(30, 48), y1 = U(48, 66); A("body", `M${f(x0)} 20 V${f(y1)} Q${f(x0)} ${f(y1 + 8)} ${f(x0 - 6)} ${f(y1 + 6)}`); J(AT.toBar, x0, 20); o.anchors.push(x0); o.r.push("Body: short blue hook hanging from the bar."); o.sub = "hang"
    }
  }
  if (body === "cross") {
    const xx = U(30, 40), yx = U(48, 58); let d;
    if (hasBar && C(.5)) { d = `M${f(xx)} 20 C${f(xx)} 30 ${f(xx)} ${f(yx - 12)} ${f(xx)} ${f(yx)}`; J(AT.toBar, xx, 20); o.anchors.push(xx); o.sig.push("frombar"); o.sub = "frombar"; o.r.push("Body: blue stroke drops from the bar…") }
    else { const sx = U(16, 24), sy = hasBar ? U(32, 36) : U(26, 32); d = `M${f(sx)} ${f(sy)} C${f(sx + 6)} ${f(sy - 6)} ${f(xx - 2)} ${f(sy - 2)} ${f(xx - 1)} ${f(sy + 6)} C${f(xx - .5)} ${f(yx - 12)} ${f(xx)} ${f(yx - 6)} ${f(xx)} ${f(yx)}`; o.sub = "hook"; o.r.push("Body: blue stroke starts with a small hook…") }
    d += ` C${f(xx)} ${f(yx + 5)} ${f(xx - 1)} ${f(yx + 9)} ${f(xx - 4)} ${f(yx + 10)} C${f(xx - 9)} ${f(yx + 11)} ${f(xx - 10)} ${f(yx + 3)} ${f(xx - 5)} ${f(yx + .5)} C${f(xx - 2)} ${f(yx - .5)} ${f(xx + 2)} ${f(yx)} ${f(xx + 6)} ${f(yx)} L${S} ${f(yx)}`;
    A("body", d); J("cross", xx, yx); J(J2, S, yx); o.r.push("…loops round, crosses itself (×), and runs straight to the stem.")
  }
  if (body === "lobes") {
    const anch = (stem === "blue" || stem === "gamma") ? S : U(56, 66), y1 = U(30, 38), cx = anch - U(14, 20), cy = y1 + U(10, 16);
    if (!(stem === "blue" || stem === "gamma")) { A("struct", `M${f(anch)} 20 V${f(y1)}`); J(AT.descenderToBar, anch, 20); o.anchors.push(anch) }
    A("body", `M${f(anch)} ${f(y1)} C${f(anch - 7)} ${f(y1 - 5)} ${f(cx + 2)} ${f(y1 - 3)} ${f(cx)} ${f(cy)}`);
    A("body", `M${f(cx)} ${f(cy)} C${f(cx - 3)} ${f(cy - 9)} ${f(cx - 13)} ${f(cy - 14)} ${f(cx - 20)} ${f(cy - 10)} C${f(cx - 27)} ${f(cy - 5)} ${f(cx - 27)} ${f(cy + 7)} ${f(cx - 19)} ${f(cy + 11)} C${f(cx - 13)} ${f(cy + 15)} ${f(cx - 7)} ${f(cy + 17)} ${f(cx - 1)} ${f(cy + 18)}`);
    J((stem === "blue" || stem === "gamma") ? J2 : AT.descenderToBody, anch, y1); J("touch", cx, cy); o.r.push("Body: two open blue lobes meeting at a cusp (○).")
  }
  if (body === "rev3") {
    const x0 = U(28, 40), cx = U(40, 48), cy = U(28, 34), ys = U(36, 46), lo = U(46, 56);
    A("body", `M${f(x0)} 20 C${f(x0 - 10)} 22 ${f(x0 - 12)} ${f(cy + 4)} ${f(x0 - 4)} ${f(cy + 5)} C${f(x0 + 2)} ${f(cy + 6)} ${f(cx - 3)} ${f(cy + 2)} ${f(cx)} ${f(cy)}`);
    A("body", `M${f(cx)} ${f(cy)} C${f(cx - 10)} ${f(cy + 4)} ${f(cx - 18)} ${f(lo - 8)} ${f(cx - 14)} ${f(lo)} C${f(cx - 8)} ${f(lo + 10)} ${f(S - 10)} ${f(ys + 8)} ${S} ${f(ys)}`);
    J(AT.toBar, x0, 20); J("touch", cx, cy); J(J2, S, ys); o.anchors.push(x0); o.r.push("Body: blue reversed 3 from the bar to the stem; two cups meet at a cusp (○).")
  }
  if (body === "U") {
    if (stem === "blue" || stem === "gamma") {
      const x1 = U(28, 38), ys = U(44, 58); A("body", `M${f(x1)} 20 V${f(ys - 14)} C${f(x1)} ${f(ys + 6)} ${f(S - 16)} ${f(ys + 8)} ${S} ${f(ys)}`); J(AT.toBar, x1, 20); J(J2, S, ys); o.anchors.push(x1);
      o.sub = "tostem"; diag = { p: [x1, 20], q: [S, f(ys)] }; o.r.push("Body: blue stroke drops from the bar and curves round into the stem.")
    } else {
      const x1 = U(26, 34), x2 = x1 + U(16, 24), dd = U(36, 50), h = U(10, 16);
      A("body", `M${f(x1)} 20 V${f(dd)} C${f(x1)} ${f(dd + h)} ${f(x2)} ${f(dd + h)} ${f(x2)} ${f(dd)} V20`); J(AT.toBar, x1, 20); J(AT.toBar, x2, 20); o.anchors.push(x1, x2);
      o.sub = "hanging"; diag = { p: [x1, 20], q: [x2, f(dd)] }; o.r.push("Body: blue U hanging from the bar at two points.")
    }
  }
  if (body === "corner") {
    const x0 = stem === "green" ? U(46, S - 10) : U(56, 70), cx = U(22, 32), cy = U(36, 46);
    A("body", `M${f(x0)} 20 C${f(x0 - 3)} 32 ${f(cx + 16)} ${f(cy - 4)} ${f(cx)} ${f(cy)}`); A("body", `M${f(cx)} ${f(cy)} C${f(cx + 2)} ${f(cy + 14)} ${f(cx + 16)} ${f(cy + 28)} ${f(x0 + 2)} ${f(cy + 30)}`);
    J(AT.toBar, x0, 20); J("touch", cx, cy); o.anchors.push(x0); o.r.push("Body: blue cornered stroke from the bar, sharp corner (○), sweeping down-right.")
  }
  if (body === "hang") {
    const k = P(Object.keys(HANG)), T = HANG[k]; o.sig.push(k); o.sub = k;
    const xmax = stem === "green" ? S - 24 : 70, xd = U(Math.max(40, xmax - 16), xmax), yd = U(30, 36), sx = U(.75, 1.3), sy = U(.75, 1.2);
    A("struct", `M${f(xd)} 20 V${f(yd)}`); J(AT.descenderToBar, xd, 20); J(AT.descenderToBody, xd, yd); o.anchors.push(xd);
    (Array.isArray(T.d) ? T.d : [T.d]).forEach(d => A("body", tf(d, T.a[0], T.a[1], sx, sy, xd, yd)));
    T.x.forEach(p => { const q = tp(p[0], p[1], T.a[0], T.a[1], sx, sy, xd, yd); J("cross", q[0], q[1]) });
    T.t.forEach(p => { const q = tp(p[0], p[1], T.a[0], T.a[1], sx, sy, xd, yd); J("touch", q[0], q[1]) });
    o.r.push(`Body: short purple descender touches the bar and holds a blue ${k}.`)
  }
  if (diag && o.sub !== "curl" && C(AT.diagonalProb)) {
    const { p, q } = diag; A("second", `M${f(p[0])} ${f(p[1])} L${f(q[0])} ${f(q[1])}`);
    o.j = o.j.filter(j => !(j.x === f(q[0]) && j.y === f(q[1])) && !(j.x === f(p[0]) && j.y === f(p[1]))); J("red", p[0], p[1]); J("red", q[0], q[1]); o.r.push("Green diagonal across the inside, red at both ends."); o.sig.push("diag")
  }
  if (stem === "blue" && !["lobes", "hook"].includes(body) && C(AT.stemTailProb)) { const y0 = U(44, 62), att = o.j.filter(j => j.x === S && j.y !== 20), y = att.length ? P(att).y : y0; A("second", `M${S} ${f(y)} C${f(S + 8)} ${f(y - 8)} ${f(S + 18)} ${f(y - 2)} ${f(S + 14)} ${f(y + 8)}`); J("red", S, y); o.r.push("Green tail curls off the stem to the right."); o.sig.push("tail") }
  // accent
  const AC = cfg.accents;
  if (hasBar && o.anchors.length && C(AC.prob)) {
    const xs = [...new Set(o.anchors.map(f))].sort((a, b) => a - b); const wh = cfg.anchors.where;
    const ax = wh === "leftmost" ? xs[0] : wh === "any" ? P(xs) : xs[xs.length - 1];
    const ty = W(AC.types), dir = ty[1] === "L" ? -1 : 1, h = U(...AC.height), c = U(...AC.curl);
    A("accent", `M${f(ax)} 20 C${f(ax)} ${f(20 - h * .8)} ${f(ax + dir * c * .5)} ${f(20 - h * 1.1)} ${f(ax + dir * c)} ${f(20 - h * .95)}`);
    if (ty[0] === "2") A("accent", `M${f(ax)} 20 C${f(ax)} ${f(20 - h * 1.2)} ${f(ax + dir * c * .5)} ${f(20 - h * 1.5)} ${f(ax + dir * c * .85)} ${f(20 - h * 1.4)}`);
    o.j = o.j.filter(j => !(j.x === f(ax) && j.y === 20)); J("red", ax, 20);
    o.r.push(`Accent: ${ty[0]} stroke${ty[0] === "2" ? "s" : ""} curling ${dir < 0 ? "left" : "right"}, on the ${wh === "any" ? "chosen" : wh} bar anchor.`); o.sig.push("acc"); o.acc = 1
  }
  o.key = [hasBar ? 1 : 0, stem, body, o.sub || "-", o.sig.filter(v => ["diag", "tail", "tail3", "acc"].includes(v)).sort().join("+")].join("|");
  return o
}
// Structural recipes that reproduce real Devanagari letters (bar | right side | body | variant | extras)
const REAL_KEYS = {
  "1|blue|loop|-|": "व", "1|blue|loop|-|diag": "ब", "1|blue|loop|-|tail": "क",
  "1|blue|cup|frombar|": "य", "1|blue|cup|frombar|tail3": "स", "1|blue|cup|hook|": "च / ज", "1|blue|cup|hook|tail3": "ञ", "0|blue|cup|hook|": "थ",
  "1|blue|hook|in|": "न", "1|blue|hook|out|": "त", "1|green|hook|hang|": "ग",
  "1|blue|cross|frombar|": "म", "0|gamma|cross|hook|": "भ",
  "1|blue|lobes|-|": "ल", "1|none|lobes|-|": "ऌ", "1|blue|rev3|-|": "घ",
  "1|blue|U|tostem|": "प", "1|blue|U|tostem|diag": "ष", "1|blue|U|tostem|tail": "फ", "1|green|U|hanging|": "ण",
  "1|none|corner|-|": "र", "1|green|hang|S-hook with crossed tail|": "झ", "1|none|hang|S-hook with crossed tail|acc": "ई"
};
for (const k of Object.keys(HANG)) REAL_KEYS[`1|none|hang|${k}|`] = { "open hook": "ट", "closed loop": "ठ", "S-hook": "ड / ङ", "S-hook with crossed tail": "इ", "loop with inner curl": "ढ", "hook with crossed curl": "द", "arc with two lower arcs": "ह" }[k];
// ---- mutation: make a new style variant of one config section ----
const MUTATE = {
  frame: c => { const s = { blue: R(), none: R(), green: R() * .6, gamma: R() * .5 }; return { ...c, barProb: f(U(.6, 1)), stem: Object.fromEntries(Object.entries(s).map(([k, v]) => [k, f(v)])), stemX: (() => { const a = U(58, 72); return [f(a), f(a + U(4, 10))] })() } },
  bodies: c => { const w = {}; for (const k in c.weights) w[k] = C(.25) ? 0 : f(U(0, 10)); if (Object.values(w).every(v => !v)) w.cup = 5; return { weights: w } },
  attach: c => ({ ...c, toBlueStem: C(.7) ? "touch" : "red", diagonalProb: f(U(0, .8)), stemTailProb: f(U(0, .5)), cornerTailProb: f(U(0, .8)) }),
  accents: c => { const t = { "1L": R(), "1R": R(), "2L": R(), "2R": R() }; for (const k in t) if (C(.35)) t[k] = 0; if (Object.values(t).every(v => !v)) t["1R"] = 1; return { prob: f(U(.1, .5)), types: Object.fromEntries(Object.entries(t).map(([k, v]) => [k, f(v)])), height: (() => { const a = U(8, 16); return [f(a), f(a + U(2, 6))] })(), curl: (() => { const a = U(3, 10); return [f(a), f(a + U(2, 8))] })() } },
  anchors: c => ({ where: P(["rightmost", "leftmost", "any"]) })
};
// ---- similarity ----
const NS = "http://www.w3.org/2000/svg"; let SVGM;
function ptsOf(o) { if (!SVGM) { SVGM = document.createElementNS(NS, "svg"); SVGM.style.position = "absolute"; SVGM.style.width = "0"; SVGM.style.height = "0"; document.body.appendChild(SVGM) } let out = []; for (const k of o.s) { const p = document.createElementNS(NS, "path"); p.setAttribute("d", k.d); SVGM.appendChild(p); const L = p.getTotalLength(), n = Math.max(2, Math.ceil(L / 2)); for (let i = 0; i <= n; i++) { const q = p.getPointAtLength(L * i / n); out.push([q.x, q.y]) } p.remove() } return out }
function half(X, Y, cap) { let s = 0; for (const x of X) { let m = 1e9; for (const y of Y) { const d = (x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2; if (d < m) m = d } s += Math.sqrt(m); if (s / X.length > cap) return 1e9 } return s / X.length }
function chamfer(A, B, cap = 1e9) { const a = half(A, B, cap * 2); if (a > cap * 2) return 1e9; return (a + half(B, A, cap * 2)) / 2 }
