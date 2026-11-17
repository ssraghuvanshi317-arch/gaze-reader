const toString = Object.prototype.toString;
export function isAnyArray(value) { const t = toString.call(value); return t.endsWith('Array]') && !t.includes('Big'); }
