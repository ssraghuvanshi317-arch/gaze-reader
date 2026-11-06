// Simulated reading: does the line tracker follow a reader through noisy gaze data?
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const core = html.match(/<script id="core">([\s\S]*?)<\/script>/)[1];
const GR = new Function('module', core + '\nreturn GR;')(undefined);

let seed = 7;
function rnd() { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }
function gauss() { const u = 1 - rnd(), v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }

function layout(nLines, width, pitch, wordsPerLine) {
  const lines = [];
  for (let i = 0; i < nLines; i++) {
    const n = wordsPerLine + Math.floor(rnd() * 3) - 1, words = [];
    // last line of a paragraph is sometimes short
    const frac = rnd() < 0.15 ? 0.3 + rnd() * 0.5 : 1;
    const used = width * frac, ww = used / n;
    for (let j = 0; j < n; j++) words.push({ l: j * ww + 4, r: (j + 1) * ww - 4, cx: (j + 0.5) * ww });
    lines.push({ cy: 30 + i * pitch, left: 0, right: used, words });
  }
  return lines;
}

// Reader model: fixations ~230 ms, mostly forward word steps, 10% regressions, return sweep that often undershoots.
function reading(lines, fps) {
  const out = []; let t = 0;
  for (let li = 0; li < lines.length; li++) {
    const L = lines[li];
    let w = rnd() < 0.5 ? 1 : 0;
    while (w < L.words.length) {
      const dur = Math.max(0.1, 0.23 + 0.06 * gauss());
      const fx = L.words[Math.min(w, L.words.length - 1)].cx + 6 * gauss();
      for (let k = 0; k < dur * fps; k++) { out.push({ t, x: fx, y: L.cy, line: li, word: w }); t += 1 / fps; }
      const r = rnd();
      w += r < 0.1 ? -1 : r < 0.3 ? 2 : 1;
      if (w < 0) w = 0;
    }
  }
  return out;
}

function run({ name, nLines = 40, width, pitch, wpl, sigma, bias, fps = 30, drift = 0 }) {
  const lines = layout(nLines, width, pitch, wpl);
  const truth = reading(lines, fps);
  const tr = new GR[process.env.TR || 'HmmTracker']({ pitch, sigmaX: sigma, sigmaY: sigma, errX: bias, errY: bias, ...JSON.parse(process.env.OPTS||'{}') });
  tr.setLines(lines);
  let ok = 0, okWord = 0, n = 0, sweeps = 0, jumps = 0, maxLag = 0, lagStart = null;
  const bx = bias * gauss(), by = bias * gauss();
  let wanderX = 0, wanderY = 0, blinkUntil = -1, log = [], prevL = 0;
  for (const s of truth) {
    // slow wander (head movement) + per-frame jitter + blinks
    wanderX += (drift * gauss() - 0.02 * wanderX); wanderY += (drift * gauss() - 0.02 * wanderY);
    if (rnd() < 0.008) blinkUntil = s.t + 0.2;
    if (s.t < blinkUntil) continue;
    const r = tr.update(s.t, s.x + bx + wanderX + sigma * gauss(), s.y + by + wanderY + sigma * gauss());
    if (r.ev === 'sweep') sweeps++; if (r.ev === 'jump') jumps++;
    if (process.env.DIV && name.includes(process.env.DIV)) {
      if (r.ev) log.push(`${s.t.toFixed(2)} ${r.ev} -> ${r.line} (truth ${s.line} w${s.word})`);
      if (s.line !== prevL) { log.push(`${s.t.toFixed(2)}   truth -> ${s.line} (tracker ${tr.cur})`); prevL = s.line; }
    }
    n++; if (r.line === s.line) { ok++; if (Math.abs(r.word - s.word) <= 1) okWord++; lagStart = null; }
    else { if (lagStart == null) lagStart = s.t; maxLag = Math.max(maxLag, s.t - lagStart); }
  }
  const endOk = tr.cur === nLines - 1;
  if (log.length) console.log(log.join('\n'));
  console.log(`${name.padEnd(34)} line-correct ${(100 * ok / n).toFixed(1).padStart(5)}%  word±1 ${(100 * okWord / n).toFixed(1).padStart(5)}%  sweeps ${String(sweeps).padStart(3)}/${nLines - 1}  jumps ${jumps}  longest-wrong ${maxLag.toFixed(1)}s  ended-on-last ${endOk}`);
  return ok / n;
}


function multi(cfg, N=12){ const r=[]; let bad=0; for(let i=0;i<N;i++){ seed=1000+i*77; const q=runQ(cfg); r.push(q.acc); if(q.maxLag>5) bad++; }
  r.sort((a,b)=>a-b); const mean=r.reduce((a,b)=>a+b,0)/N;
  console.log(`${cfg.name.padEnd(28)} mean line-correct ${(100*mean).toFixed(1).padStart(5)}%   median ${(100*r[N>>1]).toFixed(1).padStart(5)}%   runs with a >5s loss: ${bad}/${N}`); }
function runQ(cfg){ const log=console.log; let acc=0,maxLag=0; console.log=(s)=>{ const m=s.match(/line-correct\s+([\d.]+)%.*longest-wrong ([\d.]+)s/); if(m){acc=+m[1]/100;maxLag=+m[2];} }; run(cfg); console.log=log; return {acc,maxLag}; }
const cfgs = process.env.QUICK ? [] : [];
console.log('--- laptop: 600px column, pitch 49px, ~9 words/line, 30fps ---');
for (const sg of [0, 20, 40, 60, 90]) multi({ name: `laptop jitter ${sg}px`, width: 600, pitch: 49, wpl: 9, sigma: sg, bias: sg * 1.5, drift: sg / 15 });
console.log('--- phone: 350px column, pitch 42px, ~6 words/line ---');
for (const sg of [0, 30, 60, 90]) multi({ name: `phone jitter ${sg}px`, width: 350, pitch: 42, wpl: 6, sigma: sg, bias: sg * 1.5, drift: sg / 15 });
for (const sg of [30, 60]) multi({ name: `phone 15fps jitter ${sg}px`, width: 350, pitch: 42, wpl: 6, sigma: sg, bias: sg * 1.5, fps: 15, drift: sg / 15 });
if (process.env.EXTRA) {
  console.log('--- phone, bigger text: 350px col, pitch 55px, ~4 words/line ---');
  for (const sg of [30, 60, 90]) multi({ name: `phone-big jitter ${sg}px`, width: 350, pitch: 55, wpl: 4, sigma: sg, bias: sg * 1.5, drift: sg / 15 });
  console.log('--- phone landscape: 650px col, pitch 45px, ~9 words/line ---');
  for (const sg of [30, 60, 90]) multi({ name: `phone-land jitter ${sg}px`, width: 650, pitch: 45, wpl: 9, sigma: sg, bias: sg * 1.5, drift: sg / 15 });
  console.log('--- laptop, bigger text: 800px col, pitch 68px ---');
  for (const sg of [60, 90, 120]) multi({ name: `laptop-big jitter ${sg}px`, width: 800, pitch: 68, wpl: 9, sigma: sg, bias: sg * 1.5, drift: sg / 15 });
}
