import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox']); pg=b.new_page(viewport={'width':1100,'height':760})
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file://'+sys.argv[1]); pg.click('#sample'); pg.click('#goSim'); pg.wait_for_timeout(500)
    L=pg.evaluate("window.__GR_APP.lines.slice(0,6).map(l=>({cy:l.cy,xs:l.words.map(w=>w.cx)}))")
    cr=pg.evaluate("(()=>{const r=document.querySelector('#content').getBoundingClientRect();return [r.left,r.top]})()")
    res=[]
    for i,l in enumerate(L):
        for x in l['xs']:
            for k in range(4):
                pg.mouse.move(cr[0]+x, cr[1]+l['cy']); pg.wait_for_timeout(60)
        res.append(pg.evaluate("window.__GR_APP.tracker.cur"))
    print('true lines 0..5 -> tracker at end of each line:',res)
    pg.screenshot(path='/tmp/simmode.png'); print('errors',errs); b.close()
