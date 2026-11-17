// Test PDF: title (full width), two-column body with an equation, a full-width equation, a table, then a 1-column page.
import fs from 'fs';
const { PDFDocument, StandardFonts } = (await import('/opt/npm-tools/node_modules/pdf-lib/cjs/index.js')).default;
const doc = await PDFDocument.create(); const f = await doc.embedFont(StandardFonts.TimesRoman), fb = await doc.embedFont(StandardFonts.TimesRomanBold);
const L = 'alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega'.split(' ');
let wi = 0; const words = n => Array.from({ length: n }, () => L[wi++ % L.length]).join(' ');
let pg = doc.addPage([612, 792]);
pg.drawText('A Title Line Spanning The Whole Page Width For Testing', { x: 60, y: 740, size: 16, font: fb });
let y = 700;
const left = [], right = [];
for (let i = 0; i < 14; i++) { const a = 'L' + i + ' ' + words(6), b = 'R' + i + ' ' + words(6); left.push(a); right.push(b); }
left.forEach((t, i) => pg.drawText(t, { x: 60, y: 700 - i * 14, size: 10, font: f }));
right.forEach((t, i) => pg.drawText(t, { x: 320, y: 700 - i * 14, size: 10, font: f }));
pg.drawText('EQ  E = m c 2 + p v (full width equation line across the page centre)', { x: 120, y: 480, size: 12, font: f });
pg.drawText('2', { x: 178, y: 486, size: 7, font: f });  // superscript
['TBL  Material   Density   Speed', 'TBL  Steel   7850   5960', 'TBL  Water   1000   1480'].forEach((t, i) => pg.drawText(t, { x: 150, y: 440 - i * 16, size: 11, font: f }));
for (let i = 0; i < 6; i++) { pg.drawText('L2_' + i + ' ' + words(6), { x: 60, y: 370 - i * 14, size: 10, font: f }); pg.drawText('R2_' + i + ' ' + words(6), { x: 320, y: 370 - i * 14, size: 10, font: f }); }
pg = doc.addPage([612, 792]);
for (let i = 0; i < 20; i++) pg.drawText('P2_' + i + ' ' + words(12), { x: 60, y: 720 - i * 16, size: 11, font: f });
fs.writeFileSync(process.argv[2], await doc.save());
console.log('pdf written');
