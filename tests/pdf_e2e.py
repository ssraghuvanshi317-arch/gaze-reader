"""PDF page mode in headless Chrome: reading order of lines (columns, equation, table) and tracking with pointer-as-gaze.
pdf.js is served from the local pdfjs-dist build through a routed fake URL."""
import sys, json
from playwright.sync_api import sync_playwright

PAGE = 'file://' + sys.argv[1]
PDFFILE = sys.argv[2]
PJ = '/opt/npm-tools/node_modules/pdfjs-dist/legacy/build/'

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 1100, 'height': 800})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    def serve(route):
        name = route.request.url.rsplit('/', 1)[1]
        route.fulfill(path=PJ + name, headers={'content-type': 'text/javascript', 'access-control-allow-origin': '*'})
    pg.route('https://pdfjs.local.test/*', serve)
    pg.add_init_script("window.__PDFJS_ESM='https://pdfjs.local.test/pdf.mjs'; window.__PDFJS_WORKER='https://pdfjs.local.test/pdf.worker.mjs'")
    pg.goto(PAGE)
    pg.set_input_files('#file', PDFFILE)
    pg.wait_for_function("document.querySelector('#fileStatus').textContent.startsWith('Loaded')", timeout=20000)
    print(pg.inner_text('#fileStatus'))
    pg.click('#goSim')
    pg.wait_for_function("window.__GR_APP.lines.length > 10", timeout=20000)
    pg.wait_for_timeout(800)
    order = pg.evaluate("window.__GR_APP.lines.map(l => l.words.slice(0,3).map(w=>w.t).join(' '))")
    print('lines found:', len(order))
    for i, t in enumerate(order[:44]): print(f'  {i:2d}: {t}')
    # pointer-as-gaze: sweep through the first 30 lines in reading order
    L = pg.evaluate("window.__GR_APP.lines.slice(0,30).map(l=>({cy:l.cy,xs:l.words.map(w=>w.cx)}))")
    res = []
    for i, l in enumerate(L):
        cr = pg.evaluate("(()=>{const r=document.querySelector('#content').getBoundingClientRect();return [r.left,r.top]})()")
        for x in l['xs']:
            for k in range(3):
                pg.mouse.move(cr[0] + x, cr[1] + l['cy']); pg.wait_for_timeout(45)
        res.append(pg.evaluate("window.__GR_APP.tracker.cur"))
    ok = sum(1 for i, r in enumerate(res) if r == i)
    print(f'tracker on the right line at the end of {ok}/{len(res)} lines; trace: {res}')
    pg.evaluate("document.querySelector('#reader').scrollTop = 0")
    pg.wait_for_timeout(600)
    pg.screenshot(path='/tmp/pdfmode.png')
    print('errors:', errs[:5])
    b.close()
