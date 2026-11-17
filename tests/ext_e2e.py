"""External tracker mode with a fake WebSocket that streams a scripted reader's gaze (per-eye; left eye turned)."""
import sys
from playwright.sync_api import sync_playwright
MOCK = """
(() => {
  let seed = 9; const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const g = () => { const u = 1 - rnd(), v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  const R = { line: 0, word: 0, until: 0 }; window.__R = R;
  window.WebSocket = class { constructor(url) { this.readyState = 1; setTimeout(() => this.onopen && this.onopen(), 10);
      const tick = () => { const A = window.__GR_APP; if (A && A.phase === 'read' && A.lines.length) {
          const L = A.lines, t = performance.now() / 1000;
          if (t > R.until) { let w = R.word + (rnd() < 0.1 ? -1 : rnd() < 0.25 ? 2 : 1); if (w < 0) w = 0;
            if (w >= L[R.line].words.length) { if (R.line < L.length - 1) { R.line++; w = rnd() < 0.5 ? 0 : 1; } else w = L[R.line].words.length - 1; }
            R.word = Math.min(w, L[R.line].words.length - 1); R.until = t + 0.23 + 0.05 * g(); }
          const cr = document.querySelector('#content').getBoundingClientRect(), Lw = L[R.line], W = Lw.words[R.word];
          const x = (cr.left + W.cx + 25 * g()) / screen.width, y = (cr.top + Lw.cy + 25 * g()) / screen.height;
          this.onmessage && this.onmessage({ data: JSON.stringify({ r: [x, y], l: [0.2 + 0.05 * g(), 0.9] }) }); }
        this.timer = setTimeout(tick, 16); };
      tick(); }
    close() { clearTimeout(this.timer); } send() {} };
})();
"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 1280, 'height': 800}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(MOCK + "localStorage.setItem('gr.ext', JSON.stringify('ws://localhost:8765')); localStorage.setItem('gr.eye', JSON.stringify('R'));")
    pg.goto('file://' + sys.argv[1]); pg.click('#sample')
    assert not pg.is_hidden('#goExt'); pg.click('#goExt')
    ok = n = 0
    for i in range(100):
        pg.wait_for_timeout(250)
        st = pg.evaluate('({t: window.__GR_APP.tracker.cur, r: window.__R.line})'); n += 1; ok += st['t'] == st['r']
    print(f'external tracker (right eye followed, left eye turned): on the true line {100*ok/n:.0f}% of samples'); print('errors', errs[:5]); b.close()
