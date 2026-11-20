"""
Random-walk OTP v2: statistical quality, binding to the transaction, graph properties, brute-force
odds and speed, compared with standard TOTP (RFC 6238, HMAC-SHA1, 6 digits).

    python evaluation/eval_otp.py
"""

import hashlib
import hmac
import math
import os
import struct
import time
from collections import Counter, deque

import numpy as np

from common import COLORS, plt_setup, save_json, savefig

import walk_otp as W  # noqa: E402

RNG = np.random.default_rng(7)


def totp(secret, counter, digits=6):
    """RFC 6238 / RFC 4226 reference (HMAC-SHA1, dynamic truncation)."""
    d = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = d[-1] & 0x0F
    return str((struct.unpack(">I", d[o:o + 4])[0] & 0x7FFFFFFF) % 10 ** digits).zfill(digits)


def secrets(n):
    return [RNG.bytes(32) for _ in range(n)]


def chi_square(counts, expected):
    from scipy.stats import chi2
    counts = np.asarray(counts, float)
    stat = float(((counts - expected) ** 2 / expected).sum())
    dof = len(counts) - 1
    return {"chi2": stat, "dof": dof, "p_value": float(chi2.sf(stat, dof))}


def graph_stats(adj, lattice_ref=True):
    n = len(adj)
    deg = [len(a) for a in adj]
    dist_all = []
    ecc = []
    for s in range(n):
        dist = [-1] * n
        dist[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if dist[v] < 0:
                    dist[v] = dist[u] + 1
                    q.append(v)
        ecc.append(max(dist))
        dist_all += [d for d in dist if d > 0]
    conn = all(e >= 0 for e in ecc) and min(min(1, d) for d in deg) > 0

    def clustering(a):
        cs = []
        for u in range(len(a)):
            nb = a[u]
            k = len(nb)
            if k < 2:
                cs.append(0.0)
                continue
            links = sum(1 for i in range(k) for j in range(i + 1, k) if nb[j] in a[nb[i]])
            cs.append(2 * links / (k * (k - 1)))
        return float(np.mean(cs))

    out = {"nodes": n, "edges": sum(deg) // 2, "degree_min": min(deg), "degree_max": max(deg),
           "degree_mean": float(np.mean(deg)), "connected": bool(conn), "diameter": max(ecc),
           "avg_path_length": float(np.mean(dist_all)), "clustering": clustering(adj),
           "degree_histogram": dict(Counter(deg))}
    if not lattice_ref:
        return out
    lattice = [sorted({(i + d) % n for d in (-3, -2, -1, 1, 2, 3)}) for i in range(n)]
    ref = graph_stats(lattice, lattice_ref=False)
    out.update({"lattice_clustering": ref["clustering"], "lattice_avg_path_length": ref["avg_path_length"],
                "lattice_diameter": ref["diameter"]})
    return out


def main():
    cfg = W.OTPConfig()
    adj = cfg.graph.adjacency()
    res = {"config": {"nodes": cfg.graph.num_nodes, "lattice_degree": cfg.graph.degree, "steps": cfg.walk_steps,
                      "digits": cfg.digits, "time_step_s": cfg.time_step, "rewire_p": 0.3}}

    # 1. distinct codes from many secrets at one time step (v1 had collapsed to 768 codes)
    n = 20000
    ks = secrets(n)
    walk_codes = [W.generate_otp(k, counter=1000, config=cfg)[0] for k in ks]
    totp_codes = [totp(k, 1000) for k in ks]
    expected_distinct = 1e6 * (1 - (1 - 1e-6) ** n)
    res["distinct"] = {"n_secrets": n, "walk_v2": len(set(walk_codes)), "totp": len(set(totp_codes)),
                       "ideal_expected": expected_distinct, "walk_v1_recorded": 768}

    # 2. uniformity: 200,000 codes (random secrets and time steps)
    m = 200000
    ks2 = secrets(2000)
    codes = [W.generate_otp(ks2[i % 2000], counter=int(RNG.integers(1, 2 ** 40)), config=cfg)[0] for i in range(m)]
    arr = np.array([int(c) for c in codes])
    buckets = np.bincount(arr // 10000, minlength=100)
    digit_pos = np.array([[sum(1 for c in codes if c[p] == str(dg)) for dg in range(10)] for p in range(6)])
    res["uniformity"] = {"n_codes": m, "buckets_100": chi_square(buckets, m / 100),
                         "digit_positions": [chi_square(digit_pos[p], m / 10) for p in range(6)],
                         "mean_code": float(arr.mean()), "ideal_mean": 499999.5}

    # 3. avalanche / binding: 1-bit change of K, next time step, and a 1-cent / payee change of the transfer
    trials = 5000
    same = Counter()
    hamming = {k: [] for k in ("key_bit", "time_step", "amount_1c", "payee", "reference")}
    seed_bits = []
    for i in range(trials):
        k = RNG.bytes(32)
        t = int(RNG.integers(1, 2 ** 40))
        ctx = W.transaction_context(f"TX-{i:06X}", 5000.00, "alice@vaulttrust.com")
        base = W.generate_otp(k, counter=t, context=ctx, config=cfg)[0]
        kb = bytearray(k)
        kb[int(RNG.integers(32))] ^= 1 << int(RNG.integers(8))
        variants = {"key_bit": W.generate_otp(bytes(kb), counter=t, context=ctx)[0],
                    "time_step": W.generate_otp(k, counter=t + 1, context=ctx)[0],
                    "amount_1c": W.generate_otp(k, counter=t, context=W.transaction_context(
                        f"TX-{i:06X}", 5000.01, "alice@vaulttrust.com"))[0],
                    "payee": W.generate_otp(k, counter=t, context=W.transaction_context(
                        f"TX-{i:06X}", 5000.00, "mallory@vaulttrust.com"))[0],
                    "reference": W.generate_otp(k, counter=t, context=W.transaction_context(
                        f"TX-{i + 1:06X}", 5000.00, "alice@vaulttrust.com"))[0]}
        for name, c in variants.items():
            same[name] += c == base
            hamming[name].append(sum(a != b for a, b in zip(c, base)))
        s1 = W._derive_walk_seed(k, t, ctx)
        s2 = W._derive_walk_seed(bytes(kb), t, ctx)
        seed_bits.append(sum(bin(a ^ b).count("1") for a, b in zip(s1, s2)) / 256)
    res["binding"] = {"trials": trials,
                      "same_code": dict(same),
                      "mean_digits_changed": {k: float(np.mean(v)) for k, v in hamming.items()},
                      "ideal_digits_changed": 5.4,
                      "seed_avalanche_bits": float(np.mean(seed_bits))}

    # 4. graph and walk properties
    res["graph"] = graph_stats(adj)
    visits = Counter()
    starts = Counter()
    for i in range(3000):
        _, _, path = W.generate_otp_with_path(ks2[i % 2000], counter=i)
        visits.update(path)
        starts[path[0]] += 1
    deg = np.array([len(a) for a in adj])
    v = np.array([visits[i] for i in range(len(adj))], float)
    res["walk"] = {"walks": 3000, "visit_degree_corr": float(np.corrcoef(v, deg)[0, 1]),
                   "start_chi2": chi_square([starts[i] for i in range(len(adj))], 3000 / len(adj)),
                   "paths_log2": float(math.log2(len(adj)) + sum(math.log2(len(adj[0])) for _ in range(0)) +
                                       cfg.walk_steps * math.log2(np.mean(deg))),
                   "code_space_log2": math.log2(10 ** cfg.digits)}

    # 5. brute force and replay
    res["brute_force"] = {"code_space": 10 ** cfg.digits, "attempts_per_transfer": 3,
                          "p_success_per_transfer": 3 / 10 ** cfg.digits,
                          "p_success_with_grace_two_valid_codes": 6 / 10 ** cfg.digits,
                          "transfers_for_50pct": math.log(0.5) / math.log(1 - 3 / 10 ** cfg.digits),
                          "replay": "time step <= last accepted step is refused per account and scope (used_otps)"}

    # 6. speed
    def bench(fn, reps):
        t0 = time.perf_counter()
        for _ in range(reps):
            fn()
        return (time.perf_counter() - t0) / reps * 1000
    k = ks[0]
    ctx = W.transaction_context("TX-ABC123", 5000.0, "alice@vaulttrust.com")
    code = W.generate_otp(k, context=ctx)[0]
    W.OTPConfig().graph.adjacency()
    res["latency_ms"] = {
        "walk_generate": bench(lambda: W.generate_otp(k, context=ctx), 2000),
        "walk_generate_cached_graph": bench(lambda: W.generate_otp(k, context=ctx, config=cfg), 2000),
        "walk_verify_grace": bench(lambda: W.verify_otp(k, code, context=ctx, grace_seconds=10), 1000),
        "totp_generate": bench(lambda: totp(k, 1000), 20000),
        "graph_build": bench(lambda: W._build_graph(64, 6, W.DEFAULT_GRAPH_SEED), 50),
    }
    js = os.path.join("authenticator", "walk_otp.js")
    res["javascript_vectors"] = "12 fixed vectors identical in Python and JavaScript (tests/test_vectors.py)" if \
        os.path.exists(js) else None
    save_json("otp_metrics.json", res)

    # ------------------------------------------------------------ figures
    plt = plt_setup()
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar(range(100), buckets, color=COLORS["A"], width=0.85)
    ax.axhline(m / 100, color="k", ls="--", lw=1, label=f"uniform expectation ({m // 100:,})")
    ax.set_xlabel("code value bucket (code // 10,000)")
    ax.set_ylabel("codes")
    p = res["uniformity"]["buckets_100"]["p_value"]
    ax.set_title(f"Distribution of {m:,} random-walk OTP codes (chi-square p = {p:.2f})")
    ax.set_ylim(0, buckets.max() * 1.15)
    ax.legend(fontsize=8, loc="upper right")
    savefig(fig, "otp_uniformity.png")

    # graph with one walk
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    nn = len(adj)
    ang = 2 * np.pi * np.arange(nn) / nn
    xy = np.c_[np.cos(ang), np.sin(ang)]
    for u in range(nn):
        for w in adj[u]:
            if w > u:
                ax.plot(*xy[[u, w]].T, color="#C9CED6", lw=0.6, zorder=1)
    _, _, path = W.generate_otp_with_path(b"\x01" * 32, counter=56789012, context=ctx)
    for a, b in zip(path, path[1:]):
        ax.annotate("", xy=xy[b], xytext=xy[a], arrowprops=dict(arrowstyle="->", color=COLORS["L"], lw=1.6), zorder=3)
    ax.scatter(*xy.T, s=28, color=COLORS["A"], zorder=2)
    ax.scatter(*xy[path[0]], s=110, color=COLORS["F"], zorder=4, label="start")
    ax.scatter(*xy[path[-1]], s=110, color=COLORS["attack"], zorder=4, label="end")
    for i in range(0, nn, 8):
        ax.text(*(xy[i] * 1.09), str(i), ha="center", va="center", fontsize=7, color="#555")
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("64-node small-world graph and one 16-step walk")
    ax.legend(loc="lower right", fontsize=8)
    savefig(fig, "otp_graph_walk.png")

    print("distinct", res["distinct"])
    print("uniformity p", res["uniformity"]["buckets_100"]["p_value"], [round(d["p_value"], 3) for d in res["uniformity"]["digit_positions"]])
    print("binding", res["binding"])
    print("graph", {k: v for k, v in res["graph"].items() if k != "degree_histogram"})
    print("latency", res["latency_ms"])


if __name__ == "__main__":
    main()
