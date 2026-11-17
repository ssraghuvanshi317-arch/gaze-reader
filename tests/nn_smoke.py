"""Smoke test of nn.js preprocessing in Chrome: fake tf (records shapes), synthetic face landmarks, a painted video frame.
It can't judge accuracy (no real faces here); it checks the pipeline runs end to end and feeds 3 variants to the model."""
import sys
from playwright.sync_api import sync_playwright
html = """<html><body><video id=v muted playsinline></video><script src="nn.js"></script><script>
window.tf = { tidy: f => f(), browser: { fromPixels: (img) => T([img.height, img.width, 3]) },
  concat: (a, ax) => T(a[0].shape.map((d,i)=> i===ax ? a.reduce((s,t)=>s+t.shape[i],0) : d)),
  stack: (a) => T([a.length].concat(a[0].shape)), tensor2d: (v) => T([v.length, v[0].length]) };
function T(shape){ return { shape, toFloat(){return this}, div(){return this}, slice(b,s){ return T(s) } }; }
async function go(){
  const cv = document.createElement('canvas'); cv.width = 1280; cv.height = 720; const c = cv.getContext('2d');
  c.fillStyle = '#c96'; c.fillRect(0,0,1280,720); c.fillStyle='#222'; c.beginPath(); c.arc(560,330,14,0,7); c.arc(720,330,14,0,7); c.fill();
  const stream = cv.captureStream(30); const v = document.getElementById('v'); v.srcObject = stream; await v.play();
  await new Promise(r=>setTimeout(r,300));
  // synthetic landmarks: points on an ellipse face, with the indices the pipeline uses placed sensibly
  const lm = []; for (let i=0;i<478;i++){ const a = i/478*Math.PI*2*7; lm.push({x:0.5+0.12*Math.cos(a)*(0.3+0.7*(i%13)/13), y:0.47+0.2*Math.sin(a)*(0.3+0.7*(i%11)/11), z:0}); }
  const set=(i,x,y)=>lm[i]={x:x/1280,y:y/720,z:0};
  set(4,640,400); set(103,560,250); set(150,570,560); set(332,720,250); set(379,710,560); set(151,640,270); set(195,640,380);
  set(356,800,350); set(127,480,350);
  [[468,560,330],[470,560,323],[469,567,330],[472,560,337],[471,553,330],[473,720,330],[475,720,323],[474,727,330],[477,720,337],[476,713,330]].forEach(p=>set(...p));
  set(33,530,330); set(133,590,330); set(362,690,330); set(263,750,330);
  const M = {rows:4, columns:4, data:[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,-50,1]};
  const g = new NNGaze(); let seen=null;
  g.model = { predict: (inp) => { seen = inp.map(t=>t.shape); return { arraySync: () => [[0.1,0.2],[0.11,0.21],[0.09,0.19]] }; } };
  let out; const ts=[]; for (let k=0;k<15;k++){ out = g.run(v, { faceLandmarks:[lm], facialTransformationMatrixes:[M] }); ts.push(Math.round(g.ms)); } g.ms = ts.join(",");
  return { out, seen, ms: g.ms, z: g.lastZ, fw: g.faceWidthCm };
}
</script></body></html>"""
open('/home/claude/gaze-reader/_smoke.html','w').write(html)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('file:///home/claude/gaze-reader/_smoke.html')
    print(pg.evaluate('go()')); print('errors', errs); b.close()
