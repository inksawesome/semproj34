/*
 * walk_otp.js — browser/Node port of semprojOTP/otp_system/walk_otp.py (v2)
 *
 * Self-contained: ships its own SHA-256 / HMAC-SHA256 because
 * crypto.subtle is unavailable on plain-http LAN pages (phone over hotspot).
 * Byte-for-byte compatible with the Python module; see
 * semprojOTP/otp_system/tests/walk_otp_vectors.json.
 */
(function (root) {
  "use strict";

  // ------------------------------------------------------------------
  // SHA-256 (FIPS 180-4) over Uint8Array
  // ------------------------------------------------------------------
  const K256 = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);

  function sha256(msg) {
    const len = msg.length;
    const bitLen = len * 8;
    const padded = new Uint8Array(((len + 9 + 63) >> 6) << 6);
    padded.set(msg);
    padded[len] = 0x80;
    const dv = new DataView(padded.buffer);
    dv.setUint32(padded.length - 8, Math.floor(bitLen / 0x100000000));
    dv.setUint32(padded.length - 4, bitLen >>> 0);

    const H = new Uint32Array([
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ]);
    const W = new Uint32Array(64);
    const rotr = (x, n) => (x >>> n) | (x << (32 - n));

    for (let off = 0; off < padded.length; off += 64) {
      for (let i = 0; i < 16; i++) W[i] = dv.getUint32(off + i * 4);
      for (let i = 16; i < 64; i++) {
        const s0 = rotr(W[i - 15], 7) ^ rotr(W[i - 15], 18) ^ (W[i - 15] >>> 3);
        const s1 = rotr(W[i - 2], 17) ^ rotr(W[i - 2], 19) ^ (W[i - 2] >>> 10);
        W[i] = (W[i - 16] + s0 + W[i - 7] + s1) >>> 0;
      }
      let [a, b, c, d, e, f, g, h] = H;
      for (let i = 0; i < 64; i++) {
        const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        const ch = (e & f) ^ (~e & g);
        const t1 = (h + S1 + ch + K256[i] + W[i]) >>> 0;
        const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        const maj = (a & b) ^ (a & c) ^ (b & c);
        const t2 = (S0 + maj) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0;
        d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0; H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
      H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0; H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + h) >>> 0;
    }
    const out = new Uint8Array(32);
    const odv = new DataView(out.buffer);
    for (let i = 0; i < 8; i++) odv.setUint32(i * 4, H[i]);
    return out;
  }

  function concat(...arrays) {
    const total = arrays.reduce((n, a) => n + a.length, 0);
    const out = new Uint8Array(total);
    let off = 0;
    for (const a of arrays) { out.set(a, off); off += a.length; }
    return out;
  }

  function hmacSha256(key, msg) {
    if (key.length > 64) key = sha256(key);
    const k = new Uint8Array(64);
    k.set(key);
    const ipad = k.map((b) => b ^ 0x36);
    const opad = k.map((b) => b ^ 0x5c);
    return sha256(concat(opad, sha256(concat(ipad, msg))));
  }

  const utf8 = (s) => new TextEncoder().encode(s);

  function be32(n) {
    const b = new Uint8Array(4);
    new DataView(b.buffer).setUint32(0, n >>> 0);
    return b;
  }

  function be64(n) {
    const b = new Uint8Array(8);
    const dv = new DataView(b.buffer);
    dv.setUint32(0, Math.floor(n / 0x100000000));
    dv.setUint32(4, n >>> 0);
    return b;
  }

  // ------------------------------------------------------------------
  // Deterministic byte stream: SHA256(key || i_be4)
  // ------------------------------------------------------------------
  class ByteStream {
    constructor(key) { this.key = key; this.block = 0; this.buf = new Uint8Array(0); }
    take(n) {
      while (this.buf.length < n) {
        this.buf = concat(this.buf, sha256(concat(this.key, be32(this.block))));
        this.block++;
      }
      const out = this.buf.slice(0, n);
      this.buf = this.buf.slice(n);
      return out;
    }
    uint32() { return new DataView(this.take(4).buffer).getUint32(0); }
    below(n) {
      const limit = 0x100000000 - (0x100000000 % n);
      for (;;) { const x = this.uint32(); if (x < limit) return x % n; }
    }
  }

  // ------------------------------------------------------------------
  // Graph + walk + truncation (mirror of walk_otp.py)
  // ------------------------------------------------------------------
  const DEFAULTS = { numNodes: 64, degree: 6, graphSeed: 0xdeadbeef, walkSteps: 16, timeStep: 30, digits: 6 };

  function buildGraph(numNodes, degree, seed) {
    const rng = new ByteStream(sha256(concat(utf8("walk-otp-graph|"), be64(seed))));
    const half = Math.floor(degree / 2);
    const adj = Array.from({ length: numNodes }, () => new Set());
    for (let i = 0; i < numNodes; i++) {
      for (let d = 1; d <= half; d++) {
        const j = (i + d) % numNodes;
        adj[i].add(j); adj[j].add(i);
      }
    }
    for (let i = 0; i < numNodes; i++) {
      const snapshot = Array.from(adj[i]).sort((a, b) => a - b);
      for (const nb of snapshot) {
        if (!adj[i].has(nb)) continue;
        if (rng.below(1000) < 300) {
          const candidates = [];
          for (let v = 0; v < numNodes; v++) if (v !== i && !adj[i].has(v)) candidates.push(v);
          if (candidates.length > 0 && adj[nb].size > 1) {
            const newNb = candidates[rng.below(candidates.length)];
            adj[i].delete(nb); adj[nb].delete(i);
            adj[i].add(newNb); adj[newNb].add(i);
          }
        }
      }
    }
    return adj.map((s) => Array.from(s).sort((a, b) => a - b));
  }

  let cachedGraph = null;
  function graph() {
    if (!cachedGraph) cachedGraph = buildGraph(DEFAULTS.numNodes, DEFAULTS.degree, DEFAULTS.graphSeed);
    return cachedGraph;
  }

  function deriveWalkSeed(secret, counter, context) {
    return hmacSha256(secret, concat(be64(counter), sha256(utf8(context || ""))));
  }

  function performWalk(seed, adjacency, numNodes, walkSteps) {
    const s = new ByteStream(seed);
    let cur = s.below(numNodes);
    const path = [cur];
    for (let i = 0; i < walkSteps; i++) {
      const nbrs = adjacency[cur];
      cur = nbrs[s.below(nbrs.length)];
      path.push(cur);
    }
    return path;
  }

  function truncateToOtp(path, digits) {
    const enc = new Uint8Array(path.length * 2);
    const dv = new DataView(enc.buffer);
    path.forEach((n, i) => dv.setUint16(i * 2, n));
    const digest = sha256(concat(utf8("walk-otp-v2|"), enc));
    const offset = digest[31] & 0x0f;
    const code = new DataView(digest.buffer).getUint32(offset) & 0x7fffffff;
    return String(code % Math.pow(10, digits)).padStart(digits, "0");
  }

  function currentCounter(nowMs) {
    return Math.floor((nowMs === undefined ? Date.now() : nowMs) / 1000 / DEFAULTS.timeStep);
  }

  function generateOtp(secret, counter, context) {
    if (counter === undefined || counter === null) counter = currentCounter();
    const seed = deriveWalkSeed(secret, counter, context || "");
    const path = performWalk(seed, graph(), DEFAULTS.numNodes, DEFAULTS.walkSteps);
    return { otp: truncateToOtp(path, DEFAULTS.digits), counter, path };
  }

  function transactionContext(txId, amount, payee) {
    const cents = Math.round(Number(amount) * 100);
    return `TX|${txId}|${cents}|${String(payee).trim().toLowerCase()}`;
  }

  function b32ToBytes(b32) {
    const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    const clean = b32.toUpperCase().replace(/=+$/, "");
    let bits = 0, value = 0;
    const out = [];
    for (const ch of clean) {
      const idx = alphabet.indexOf(ch);
      if (idx < 0) throw new Error("bad base32");
      value = (value << 5) | idx; bits += 5;
      if (bits >= 8) { out.push((value >>> (bits - 8)) & 0xff); bits -= 8; }
    }
    return new Uint8Array(out);
  }

  const toHex = (u8) => Array.from(u8, (b) => b.toString(16).padStart(2, "0")).join("");

  const api = { sha256, hmacSha256, graph, generateOtp, transactionContext, currentCounter, b32ToBytes, toHex, DEFAULTS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.WalkOTP = api;
})(typeof self !== "undefined" ? self : this);
