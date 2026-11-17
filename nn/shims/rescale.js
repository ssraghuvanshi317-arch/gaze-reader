export default function rescale(input, options = {}) {
  let min = Infinity, max = -Infinity; for (const v of input) { if (v < min) min = v; if (v > max) max = v; }
  const out = options.output || new Array(input.length), a = options.min ?? 0, b = options.max ?? 1, f = (b - a) / ((max - min) || 1);
  for (let i = 0; i < input.length; i++) out[i] = (input[i] - min) * f + a; return out;
}
