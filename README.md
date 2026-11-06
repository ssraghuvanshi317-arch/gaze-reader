# Gaze Reader

Keeps your place while you read on a screen. The front camera tracks your eyes, and the app highlights the line you're on, with a rough underline under the words you're probably looking at.

Everything runs in the browser. Camera frames never leave the device.

## How it works

1. **Face landmarks**: MediaPipe Face Landmarker (loaded from jsDelivr) finds your irises, eyelids and head pose in each camera frame.
2. **Calibration**: you follow 13 dots. Ridge regression maps eye features to screen points, choosing the feature set and regularisation per axis by leave-one-dot-out cross-validation. You get an honest error estimate in pixels and in lines.
3. **Reading model (HMM)**: the hidden state is the word you're on. Each frame the eye stays put, hops forward 1–3 words, regresses 1–2, or (from the end of a line) makes a return sweep to the start of the next line. The noisy gaze point is weighed against this model over many frames. One bad frame can't move the highlight, but a real return sweep does. The vertical offset is learned while you read.
4. **Fallbacks**: tap or click a line to set it. Use ↑/↓ (or J/K). **Fix** re-centres with one dot after you move. Big held jumps (skipping ahead several lines) are caught separately.

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

```
node tests/sim.js index.html                       # tracker simulation (HmmTracker, used by the app)
TR=LineTracker node tests/sim.js index.html        # older heuristic sweep detector, for comparison
python3 tests/e2e.py $PWD/index.html               # full app in headless Chrome with a simulated face
```
