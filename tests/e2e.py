"""End-to-end test in headless Chrome with a simulated face (no real camera available here).
The mock produces MediaPipe-style landmarks whose iris offset depends on a hidden 'true gaze' point:
the calibration dot during calibration, and a scripted reader moving through the real laid-out text afterwards."""
import sys, json, time
from playwright.sync_api import sync_playwright

PAGE = 'file://' + sys.argv[1]
VIEW = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {"width": 1280, "height": 800}
NOISE = float(sys.argv[3]) if len(sys.argv) > 3 else 0.012   # iris noise in eye-widths (~0.01 = realistic-ish)
OUT = sys.argv[4] if len(sys.argv) > 4 else '/tmp/e2e'

MOCK = """
(() => {
  const rnd = (() => { let s = 12345; return () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296; })();
  const g = () => { const u = 1 - rnd(), v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  const NOISE = %NOISE%;
  const R = { line: 0, word: 0, until: 0, truthLine: 0, started: false };
  let wander = [0, 0];
  function target(t, phase) {
    if (phase === 'calib') {
      const d = document.querySelector('#cdot');
      if (d && d.style.display === 'block') { const r = d.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }
      return [innerWidth / 2, innerHeight / 2];
    }
    if (phase === 'qf') { const d = document.querySelector('#qf .d').getBoundingClientRect(); return [d.left + 15, d.top + 15]; }
    if (phase === 'read') {
      const A = window.__GR_APP, L = A.lines; if (!L.length) return [0, 0];
      if (!R.started) { R.started = true; R.line = A.tracker.cur; R.word = 0; R.until = t + 0.25; }
      if (t > R.until) {
        const r = rnd(); let w = R.word + (r < 0.1 ? -1 : r < 0.3 ? 2 : 1);
        if (w < 0) w = 0;
        if (w >= L[R.line].words.length) { if (R.line < L.length - 1) { R.line++; w = rnd() < 0.5 ? 0 : 1; } else w = L[R.line].words.length - 1; }
        R.word = Math.min(w, L[R.line].words.length - 1); R.until = t + Math.max(0.1, 0.23 + 0.06 * g());
      }
      const cr = document.querySelector('#content').getBoundingClientRect();
      const Lw = L[R.line], W = Lw.words[R.word];
      return [cr.left + W.cx, cr.top + Lw.cy];
    }
    return [innerWidth / 2, innerHeight / 2];
  }
  window.__MOCK_R = R;
  window.__GR_MOCK = { W: 640, H: 480, face(t, phase) {
    const [tx, ty] = target(t, phase);
    wander[0] = 0.98 * wander[0] + 0.002 * g(); wander[1] = 0.98 * wander[1] + 0.002 * g();
    // gaze -> iris offset in eye-width units (non-linear, like a real eyeball)
    const nx = tx / innerWidth - 0.5, ny = ty / innerHeight - 0.5;
    const u = 0.16 * Math.sin(nx * 1.4) + NOISE * g() + wander[0];
    const v = 0.07 * ny + 0.02 * ny * ny + NOISE * 0.8 * g() + wander[1];
    const lm = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5, z: 0 }));
    const set = (i, x, y) => { lm[i] = { x: x / 640, y: y / 480, z: 0 }; };
    const eye = (oc, ic, up, dn, ir, cx) => {
      const w = 60; const ax = cx - w / 2, bx = cx + w / 2, cy = 220;
      set(oc, ax, cy); set(ic, bx, cy);
      set(up, cx, cy - 12 + 6 * ny); set(dn, cx, cy + 12);
      set(ir, cx + u * w, cy + v * w);
    };
    eye(33, 133, 159, 145, 468, 260);   // image-left eye: outer(33) at left, inner(133) at right
    eye(362, 263, 386, 374, 473, 380);  // image-right eye: inner(362) at left, outer(263) at right
    set(1, 320, 280);
    const cats = [
      ['eyeLookDownLeft', Math.max(0, ny) * 0.8], ['eyeLookDownRight', Math.max(0, ny) * 0.8],
      ['eyeLookUpLeft', Math.max(0, -ny) * 0.8], ['eyeLookUpRight', Math.max(0, -ny) * 0.8],
      ['eyeLookInRight', Math.max(0, nx) * 0.6], ['eyeLookOutLeft', Math.max(0, nx) * 0.6],
      ['eyeLookOutRight', Math.max(0, -nx) * 0.6], ['eyeLookInLeft', Math.max(0, -nx) * 0.6],
      ['eyeBlinkLeft', 0.05], ['eyeBlinkRight', 0.05]
    ].map(([n, s]) => ({ categoryName: n, score: Math.min(1, s + 0.05 * g() * 0.3) }));
    return { faceLandmarks: [lm], faceBlendshapes: [{ categories: cats }] };
  } };
})();
""".replace('%NOISE%', str(NOISE))

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    ctx = b.new_context(viewport=VIEW, device_scale_factor=1)
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: errors.append('console.' + m.type + ': ' + m.text) if m.type == 'error' else None)
    pg.add_init_script(MOCK)
    pg.goto(PAGE)
    pg.screenshot(path=OUT + '_home.png')
    pg.click('#sample')
    pg.click('#goCam')
    pg.wait_for_timeout(800)
    pg.screenshot(path=OUT + '_setup.png')
    assert not pg.is_disabled('#toCalib'), 'calibrate button still disabled'
    pg.click('#toCalib'); pg.click('#calibStart')
    pg.wait_for_selector('#calibRes:not([hidden])', timeout=60000)
    print('calibration result:', pg.inner_text('#calibAcc'))
    pg.screenshot(path=OUT + '_calib.png')
    pg.click('#calibRead')
    ok = n = 0
    for i in range(160):          # ~40 s of reading
        pg.wait_for_timeout(250)
        st = pg.evaluate('({t: window.__GR_APP.tracker.cur, r: window.__MOCK_R.line, w: window.__GR_APP.tracker.word, rw: window.__MOCK_R.word})')
        n += 1; ok += st['t'] == st['r']
        if i == 60: pg.screenshot(path=OUT + '_read.png')
    print(f'reading: tracker on the true line {100*ok/n:.0f}% of samples; ended tracker line {st["t"]} vs true {st["r"]}')
    print('errors:', errors[:10])
    b.close()
