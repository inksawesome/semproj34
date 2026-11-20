const crypto = require('crypto');

const DEFAULT_NUM_NODES = 64;
const DEFAULT_DEGREE = 6;
const DEFAULT_WALK_STEPS = 16;
const DEFAULT_TIME_STEP = 30;
const DEFAULT_DIGITS = 6;
const DEFAULT_GRAPH_SEED = 0xDEADBEEF;

// Mulberry32 deterministic PRNG
function mulberry32(a) {
    return function() {
        var t = a += 0x6D2B79F5;
        t = Math.imul(t ^ t >>> 15, t | 1);
        t ^= t + Math.imul(t ^ t >>> 7, t | 61);
        return ((t ^ t >>> 14) >>> 0) / 4294967296;
    }
}

// Build deterministic graph mimicking Watts-Strogatz small-world
function buildGraph(numNodes, degree, seed) {
    const prng = mulberry32(seed);
    const half = Math.floor(degree / 2);
    const adj = Array.from({length: numNodes}, () => new Set());

    for (let i = 0; i < numNodes; i++) {
        for (let d = 1; d <= half; d++) {
            let j = (i + d) % numNodes;
            adj[i].add(j);
            adj[j].add(i);
        }
    }

    const rewireProb = 0.30;
    for (let i = 0; i < numNodes; i++) {
        const neighbours = Array.from(adj[i]);
        for (const nb of neighbours) {
            if (prng() < rewireProb) {
                const candidates = [];
                for (let v = 0; v < numNodes; v++) {
                    if (v !== i && !adj[i].has(v)) candidates.push(v);
                }
                if (candidates.length > 0) {
                    const newNb = candidates[Math.floor(prng() * candidates.length)];
                    adj[i].delete(nb);
                    adj[nb].delete(i);
                    adj[i].add(newNb);
                    adj[newNb].add(i);
                }
            }
        }
    }
    return adj.map(s => Array.from(s).sort((a,b) => a - b));
}

const _GRAPH = buildGraph(DEFAULT_NUM_NODES, DEFAULT_DEGREE, DEFAULT_GRAPH_SEED);

function currentCounter() {
    return Math.floor(Date.now() / 1000 / DEFAULT_TIME_STEP);
}

function deriveWalkSeed(secretBuf, counter) {
    const counterBuf = Buffer.alloc(8);
    counterBuf.writeBigUInt64BE(BigInt(counter), 0);
    return crypto.createHmac('sha256', secretBuf).update(counterBuf).digest();
}

function performWalk(seedBuf) {
    const startInt = Number(seedBuf.readBigUInt64BE(0));
    let currentNode = startInt % DEFAULT_NUM_NODES;
    
    const prngSeed = seedBuf.readUInt32BE(0);
    const prng = mulberry32(prngSeed);

    const path = [currentNode];
    for (let i = 0; i < DEFAULT_WALK_STEPS; i++) {
        const neighbours = _GRAPH[currentNode];
        currentNode = neighbours[Math.floor(prng() * neighbours.length)];
        path.push(currentNode);
    }
    return path;
}

function truncateToOTP(path) {
    const encoded = Buffer.alloc(path.length * 2);
    for (let i = 0; i < path.length; i++) {
        encoded.writeUInt16BE(path[i], i * 2);
    }
    
    const offset = encoded[encoded.length - 1] & 0x0F;
    const clampedOffset = offset % Math.max(1, encoded.length - 3);
    const codeInt = encoded.readUInt32BE(clampedOffset) & 0x7FFFFFFF;
    
    return (codeInt % Math.pow(10, DEFAULT_DIGITS)).toString().padStart(DEFAULT_DIGITS, '0');
}

function generateOTP(secretBuf, counter = currentCounter()) {
    const seedBuf = deriveWalkSeed(secretBuf, counter);
    const path = performWalk(seedBuf);
    return {
        otp: truncateToOTP(path),
        counter: counter,
        path: path
    };
}

function verifyOTP(secretBuf, submittedOtp, window = 1) {
    const tNow = currentCounter();
    for (let delta = -window; delta <= window; delta++) {
        const tCheck = tNow + delta;
        const expected = generateOTP(secretBuf, tCheck).otp;
        if (expected === submittedOtp) {
            return { valid: true, matchedCounter: tCheck };
        }
    }
    return { valid: false, matchedCounter: -1 };
}

module.exports = {
    generateSecret: () => crypto.randomBytes(32),
    generateOTP,
    verifyOTP,
    currentCounter,
    DEFAULT_TIME_STEP,
    DEFAULT_GRAPH_SEED,
    _GRAPH
};
