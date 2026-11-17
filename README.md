# Gaze Reader

Keeps your place while you read on a screen. The front camera tracks your eyes, and the app highlights the line you're on, with a rough underline under the words you're probably looking at.

Everything runs in the browser. Camera frames never leave the device.

## How it works

1. **Face landmarks**: MediaPipe Face Landmarker (loaded from jsDelivr) finds your irises, eyelids and head pose in each camera frame.
2. **Calibration**: you follow 13 dots. Ridge regression maps eye features to screen points, choosing the feature set and regularisation per axis by leave-one-dot-out cross-validation. You get an honest error estimate in pixels and in lines.
3. **Reading model (HMM)**: the hidden state is the word you're on. Each frame the eye stays put, hops forward 1–3 words, regresses 1–2, or (from the end of a line) makes a return sweep to the start of the next line. The noisy gaze point is weighed against this model over many frames. One bad frame can't move the highlight, but a real return sweep does. The vertical offset is learned while you read.
4. **Fallbacks**: tap or click a line to set it. Use ↑/↓ (or J/K). **Fix** re-centres with one dot after you move. Big held jumps (skipping ahead several lines) are caught separately.

## Eyes that don't point at the same place

The feature extractor builds separate feature sets for each eye (iris position, eyelids, that eye's blendshapes, head pose) as well as the averaged both-eyes set. Calibration fits every set and keeps the one that best predicts dots it hasn't seen. So with a turned or weak eye, the app follows the eye that actually looks at the dots, and the other eye is ignored. A blink counts only when *both* eyes close, so an eye that always looks half-closed doesn't make every frame get thrown away. With a simulated turned eye (in tests/e2e.py), the old both-eyes approach stayed on the right line 24% of the time; per-eye auto-selection got 98–99%. You can also force an eye in Settings.

## What's new (Nov 2026)

- **Blendshape pairing is tested, not guessed.** At calibration, the app checks which side's eyeLook* scores move with which eye's iris and locks that in. That leaves 3 candidates (both eyes, right eye, left eye) instead of 7. Fewer candidates also means less chance of picking one that only looked good by luck.
- **Distance compensation.** Moving closer makes the same eye rotation land nearer the screen point straight ahead of your eyes. Predictions are rescaled by (face size at calibration / face size now). In a geometric test (`tests/distance.js`), leaning in from 55 to 41 cm went from 3.6 cm error (2.3 lines) to 0.9 cm (0.8 lines).
- **Read-along calibration (default).** Five lines of text spread over the screen; a highlight steps word by word and you read along. This calibrates your eyes doing what they do while reading. The 13 dots are still in Settings.
- **PDF page mode.** Real pages are rendered, and lines come from the PDF's text positions: superscripts are merged into their line, two-column stretches are read left column then right, and full-width equations and tables stay in place. Scanned PDFs with no text layer can't be tracked.
- **Recording.** Camera sessions record numbers only (both eyes' features, the gaze estimate, the tracker's line, and your taps, arrows and Fixes) to IndexedDB. Export goes through the share sheet (choose Google Drive) or as a download.
- **Neural model.** WebEyeTrack's BlazeGaze (MIT) runs on a 512×128 eye strip in three variants: as-is, the right-eye half copied over the left, and the left-eye half copied over the right. Calibration compares these with the landmark methods and keeps the best.
- **External tracker.** `ws://localhost:PORT` with `{"l":[x,y],"r":[x,y]}` or `{"x","y"}` in screen fractions. See `bridges/tobii_pro_bridge.py`. The consumer Tobii Eye Tracker 5 needs Tobii's Game Integration API instead; that bridge isn't written yet.
- Auto-scroll now triggers when your line passes 78% of the screen height.

## Honest limits

- A webcam's gaze error is a few centimetres, so the word underline is approximate. The line band is the reliable part.
- Long lines track far better than short ones: the return sweep is the main signal, and it's bigger on long lines. **On a phone, read in landscape.**
- If you move your head or the device a lot, press **Fix** or recalibrate.
- Simulation results (`tests/sim.js`, synthetic readers with camera-like noise):
  - Laptop, 600 px column: about 95% of reading time on the correct line, even at 90 px jitter.
  - Phone in landscape: about 96–99%.
  - Phone in portrait at 60 px jitter: only about 73%.

  Real-world accuracy still has to be measured with a real camera.

## Running it

The camera only works over **https://** (or as a local file in Chrome/Edge on a computer).

- **GitHub Pages**: push this folder to a repo, then turn on Settings → Pages → Deploy from branch (`main`, root). Open `https://<user>.github.io/<repo>/` on any device. On iPhone use Safari, allow the camera, and use Share → Add to Home Screen for an app icon.
- **Locally on Windows**: open `index.html` in Chrome or Edge and allow the camera.

## Tests

Nothing here has run on a real eye: the camera tests use a scripted fake face. The neural model is only smoke-tested (its preprocessing runs and the three variants reach the model), because there are no real face images in the test environment.


```
node tests/sim.js index.html                       # tracker simulation (HmmTracker, used by the app)
TR=LineTracker node tests/sim.js index.html        # older heuristic sweep detector, for comparison
python3 tests/e2e.py $PWD/index.html               # full app in headless Chrome with a simulated face
```

python3 tests/pdf_e2e.py $PWD/index.html some.pdf   # PDF page mode: reading order + tracking
node tests/distance.js index.html                 # moving closer/further after calibration
python3 tests/ext_e2e.py $PWD/index.html           # external tracker over (fake) WebSocket
python3 tests/nn_smoke.py                          # neural model preprocessing smoke test

## Credits

`web/` (BlazeGaze weights) and `nn/vendor/` come from [WebEyeTrack](https://github.com/RedForestAi/WebEyeTrack) (MIT, Davalos et al. 2025). The matrix maths is ml-matrix (MIT). `nn.js` is built with: `esbuild nn/nn.ts --bundle --format=iife --minify` (see the commit history for the aliases used).
