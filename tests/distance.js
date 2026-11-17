// How much does moving closer/further after calibration hurt, and does scale compensation fix it?
// Geometric eye model: eyeball radius 12 mm, eye width 30 mm -> iris shift in eye-widths = 0.4*sin(angle).
const fs = require('fs');
const html = fs.readFileSync(process.argv[2] || 'index.html', 'utf8');
const GR = new Function('module', html.match(/<script id="core">([\s\S]*?)<\/script>/)[1] + '\nreturn GR;')(undefined);

let seed = 3; const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
const gauss = () => { const u = 1 - rnd(), v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };

function feats(tx, ty, D, dev) {   // tx,ty: target in cm relative to camera (y down); eyes at (0, dev.eyeY) cm, distance D cm
  const ex = 0, ey = dev.eyeY;
  const ax = Math.atan2(tx - ex, D), ay = Math.atan2(ty - ey, D);
  const n = 0.004;                                    // iris noise (eye-widths)
  const u = 0.4 * Math.sin(ax) + n * gauss(), v = 0.4 * Math.sin(ay) * 0.8 + n * gauss();
  const s = 6.3 / D * dev.camK;                         // interocular 6.3 cm -> fraction of frame width
  const head = [0, -0.1, 0.5 + ex / D * dev.camK, 0.45 + ey / D * dev.camK, s];
  const both = [u, v, 0.3 - 0.05 * v, 0, 0].concat(head);
  return { f: both, modes: { both }, head: { cx: head[2], cy: head[3], s } };
}

function run(dev) {
  const px = dev.pxPerCm, W = dev.wCm, H = dev.hCm;
  const toCm = (x, y) => [x / px - W / 2, y / px + dev.camGap];   // screen px -> cm from camera (camera above screen centre)
  const pts = [[.5, .5], [.08, .08], [.5, .08], [.92, .08], [.92, .5], [.92, .92], [.5, .92], [.08, .92], [.08, .5], [.29, .29], [.71, .29], [.71, .71], [.29, .71]];
  const samples = [];
  pts.forEach((p, i) => { const x = p[0] * W * px, y = p[1] * H * px; for (let k = 0; k < 20; k++) { const [cx, cy] = toCm(x, y); const F = feats(cx, cy, dev.D0, dev); samples.push({ f: F.f, modes: F.modes, x, y, pid: i }); } });
  const model = GR.calibrate(samples, 'both');
  const s0 = GR.median(samples.map(s => s.modes.both[9]));
  console.log(`\n${dev.name}: calibrated at ${dev.D0} cm; line pitch ${dev.pitchCm} cm`);
  console.log('distance   error (no fix)        error (with scale fix)');
  for (const f of [0.75, 0.85, 0.9, 1, 1.1, 1.2]) {
    const D = dev.D0 * f; let e0 = 0, e1 = 0, ey0 = 0, ey1 = 0, n = 0;
    for (let gx = 0.1; gx <= 0.9; gx += 0.2) for (let gy = 0.1; gy <= 0.9; gy += 0.2) {
      const x = gx * W * px, y = gy * H * px, [cx, cy] = toCm(x, y);
      for (let k = 0; k < 10; k++) {
        const F = feats(cx, cy, D, dev);
        const p = GR.predictGaze(model, F), q = GR.distanceFix ? GR.distanceFix(model, F, p) : p;
        e0 += Math.hypot(p.x - x, p.y - y); e1 += Math.hypot(q.x - x, q.y - y); ey0 += Math.abs(p.y - y); ey1 += Math.abs(q.y - y); n++;
      }
    }
    const L = v => (v / n / px / dev.pitchCm).toFixed(1);
    console.log(`${String(Math.round(D)).padStart(4)} cm   ${(e0 / n / px).toFixed(2)} cm (${L(ey0)} lines vert)   ${(e1 / n / px).toFixed(2)} cm (${L(ey1)} lines vert)`);
  }
}
run({ name: 'Laptop', D0: 55, wCm: 30, hCm: 19, pxPerCm: 50, camGap: 1, eyeY: 4, camK: 1.2, pitchCm: 1.0 });
run({ name: 'iPhone landscape', D0: 30, wCm: 14, hCm: 6.5, pxPerCm: 55, camGap: 0, eyeY: 3.5, camK: 1.5, pitchCm: 0.8 });
