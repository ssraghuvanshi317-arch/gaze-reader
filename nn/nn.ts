// Neural gaze estimate (BlazeGaze from WebEyeTrack, MIT licence) adapted for eyes that don't point together.
// The model sees one image strip containing both eyes. With a turned eye, that eye's half of the strip lies about
// where you're looking. So besides the normal strip we also run two edited strips where one eye's half is copied
// over the other's: "only trust the right eye" and "only trust the left eye". Calibration then picks whichever
// variant (or the landmark method) predicts your gaze best.
import {
  computeHomography, applyHomography, warpImageData, createPerspectiveMatrix, createIntrinsicsMatrix, translateMatrix,
  faceReconstruction, estimateFaceWidth, getHeadVector, computeFaceOrigin3D
} from './vendor/utils/mathUtils';

declare const tf: any;

// Same eye strip as WebEyeTrack's obtainEyePatch (face warped to a 512x512 square, rows between landmarks 151 and 195
// cut out, resized to 512x128), but done as ONE warp straight from the camera frame: ~4x less pixel work.
function eyeStrip(frame: ImageData, px: number[][]): ImageData {
  const c = px[4], pad = [0.4, 0.2];
  const src = [px[103], px[150], px[379], px[332]].map(([x, y]) => [x + (x - c[0]) * pad[0], y + (y - c[1]) * pad[1]]);
  const H = computeHomography(src, [[0, 0], [0, 512], [512, 512], [512, 0]]);
  const top = Math.round(applyHomography(H, px[151])[1]), bot = Math.round(applyHomography(H, px[195])[1]);
  const k = 128 / Math.max(1, bot - top);
  const A = [[1, 0, 0], [0, k, -top * k], [0, 0, 1]];
  const Hf = A.map(r => [0, 1, 2].map(j => r[0] * H[0][j] + r[1] * H[1][j] + r[2] * H[2][j]));
  return warpImageData(frame, Hf, 512, 128);
}

export class NNGaze {
  model: any = null;
  persp: any = null;
  K: any = null;
  kSize = '';
  faceWidthCm = -1;
  lastZ = 60;
  canvas: HTMLCanvasElement | OffscreenCanvas | null = null;
  ms = 0;

  async init(base: string): Promise<void> {
    try { await tf.setBackend('webgl'); } catch (e) { /* falls back to whatever tf picks */ }
    await tf.ready();
    this.model = await tf.loadLayersModel(base.replace(/\/$/, '') + '/web/model.json');
    // warm-up so the first real frame isn't slow
    tf.tidy(() => this.model.predict([tf.zeros([1, 128, 512, 3]), tf.zeros([1, 3]), tf.tensor2d([[0, 0, 60]])]));
  }

  // video frame + MediaPipe result -> {R, L, both} gaze outputs (normalised screen units, roughly -0.5..0.5)
  run(video: HTMLVideoElement, result: any): { both: number[], R: number[], L: number[] } | null {
    if (!this.model || !result.facialTransformationMatrixes || !result.facialTransformationMatrixes.length) return null;
    const t0 = performance.now();
    const vw = video.videoWidth, vh = video.videoHeight; if (!vw || !vh) return null;
    const w = Math.min(640, vw), h = Math.round(vh * w / vw);       // smaller frame: much cheaper, eyes still ~40 px wide
    if (!this.canvas) this.canvas = document.createElement('canvas');
    const cv: any = this.canvas; if (cv.width !== w) { cv.width = w; cv.height = h; }
    const ctx = cv.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(video, 0, 0, w, h);
    const frame: ImageData = ctx.getImageData(0, 0, w, h);
    const lm = result.faceLandmarks[0];
    const px = lm.map((l: any) => [Math.floor(l.x * w), Math.floor(l.y * h)]);
    const key = w + 'x' + h;
    if (this.kSize !== key) { this.persp = createPerspectiveMatrix(w / h); this.K = createIntrinsicsMatrix(w, h); this.kSize = key; }
    const patch = eyeStrip(frame, px);
    const faceRT = translateMatrix(result.facialTransformationMatrixes[0]);
    if (this.faceWidthCm < 0) this.faceWidthCm = estimateFaceWidth(px);
    const [, metricFace] = faceReconstruction(this.persp, lm.map((l: any) => [l.x, l.y]) as any, faceRT, this.K, this.faceWidthCm, w, h, this.lastZ);
    const origin = computeFaceOrigin3D(metricFace);
    this.lastZ = origin[2] || this.lastZ;
    const head = getHeadVector(faceRT);
    const out = tf.tidy(() => {
      const img = tf.browser.fromPixels(patch).toFloat().div(255);          // [128,512,3]; left half = image-left eye
      const left = img.slice([0, 0, 0], [128, 256, 3]), right = img.slice([0, 256, 0], [128, 256, 3]);
      const batch = tf.stack([img, tf.concat([left, left], 1), tf.concat([right, right], 1)]);
      const hv = tf.tensor2d([head, head, head]), fo = tf.tensor2d([origin, origin, origin]);
      let y = this.model.predict([batch, hv, fo]); if (Array.isArray(y)) y = y[0];
      return y.arraySync();
    });
    this.ms = performance.now() - t0;
    // image-left eye in an unmirrored camera frame = the person's right eye
    return { both: out[0], R: out[1], L: out[2] };
  }
}

(window as any).NNGaze = NNGaze;
