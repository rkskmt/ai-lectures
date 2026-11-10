# Measures every number asserted in clustering-kmeans.qmd with the deck's own
# from-scratch k-means (distance / assign / update / init_centroids / kmeans /
# sse / kmeans_best, all on two 1-D coordinate arrays), so that
# doc/measured-log.md can be written from this output and never from memory.
#
#   data : everything is read straight out of the .qmd so it cannot drift:
#          - brightness / weights: the 80 points (the 40 Salmon + 40 Sea bass
#            of the earlier decks in a fixed shuffled order)
#          - bx / by: the frozen 5-blob data (on its slide and in the Tweak
#            base code; both copies must match)
#          - init_A / init_B: the frozen initial centroids (point indices)
#          - cx_moved / cy_moved: the frozen moved centroids of the
#            local-minimum figure
#   init : random starts use the deck's init_centroids (np.random.shuffle);
#          the deck does not seed its student cells, so properties of random
#          starts are checked over many runs here. The slides state no
#          frequencies of random runs (2026-11-10); those numbers are only
#          evidence for qualitative statements.
#
# Usage: python tools/measure_clustering_kmeans.py    (from the repo root)

import ast
import re
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "clustering-kmeans.qmd"


def load_deck():
    src = DECK.read_text(encoding="utf-8")

    def arrays(name):
        pat = r"^" + name + r"\s*=\s*np\.array\((\[.*?\])\)"
        return [np.array(ast.literal_eval(m.group(1)), dtype=float)
                for m in re.finditer(pat, src, re.S | re.M)]

    def lists(name):
        pat = r"^" + name + r"\s*=\s*(\[[^\]]*\])"
        return [ast.literal_eval(m.group(1)) for m in re.finditer(pat, src, re.M)]

    (brightness,), (weights,) = arrays("brightness"), arrays("weights")
    assert brightness.shape == weights.shape == (80,)
    bxs, bys = arrays("bx"), arrays("by")
    assert len(bxs) == len(bys) == 2, "expected bx/by on the blob slide and in the Tweak base code"
    assert np.array_equal(bxs[0], bxs[1]) and np.array_equal(bys[0], bys[1]), "Tweak copy drifted"
    bx, by = bxs[0], bys[0]
    assert bx.shape == by.shape == (400,)
    (init_A,), (init_B,) = lists("init_A"), lists("init_B")
    (cx_moved,), (cy_moved,) = arrays("cx_moved"), arrays("cy_moved")
    return brightness, weights, bx, by, init_A, init_B, cx_moved, cy_moved


# ---- the deck's functions ----

def distance(x1, y1, x2, y2):
    return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def assign_deck(xs, ys, cx, cy):
    """The slide's assign verbatim: one point at a time. Too slow for the
    thousands of runs below, so the measurements use assign() and main()
    first checks that the two give identical labels."""
    labels = []
    for i in range(len(xs)):
        dists = []
        for j in range(len(cx)):
            dists.append(distance(xs[i], ys[i], cx[j], cy[j]))
        labels.append(np.argmin(dists))
    return np.array(labels)


def assign(xs, ys, cx, cy):
    """Same arithmetic as distance() per element, evaluated for all points at once."""
    dists = np.array([distance(xs, ys, cx[j], cy[j]) for j in range(len(cx))])
    return np.argmin(dists, axis=0)


def update(xs, ys, labels, cx, cy):
    new_cx, new_cy = [], []
    for j in range(len(cx)):
        mask = labels == j
        if np.sum(mask) > 0:
            new_cx.append(xs[mask].mean())
            new_cy.append(ys[mask].mean())
        else:
            new_cx.append(cx[j])
            new_cy.append(cy[j])
    return np.array(new_cx), np.array(new_cy)


def init_centroids(xs, ys, k):
    idx = np.arange(len(xs))
    np.random.shuffle(idx)
    return xs[idx[:k]], ys[idx[:k]]


def kmeans_traced(xs, ys, cx, cy):
    """Deck's kmeans plus: number of assign/update rounds and whether any
    cluster was ever empty (update then kept its centroid)."""
    k = len(cx)
    empty = False
    for step in range(1, 101):
        labels = assign(xs, ys, cx, cy)
        if np.min(np.bincount(labels, minlength=k)) == 0:
            empty = True
        new_cx, new_cy = update(xs, ys, labels, cx, cy)
        if np.all(new_cx == cx) and np.all(new_cy == cy):
            break
        cx, cy = new_cx, new_cy
    return labels, cx, cy, step, empty


def kmeans(xs, ys, cx, cy):
    labels, cx, cy, _, _ = kmeans_traced(xs, ys, cx, cy)
    return labels, cx, cy


def sse(xs, ys, labels, cx, cy):
    total = 0.0
    for j in range(len(cx)):
        mask = labels == j
        total += np.sum((xs[mask] - cx[j]) ** 2 + (ys[mask] - cy[j]) ** 2)
    return total


def kmeans_best(xs, ys, k, n_init=10):
    best_score = None
    for trial in range(n_init):
        cx, cy = init_centroids(xs, ys, k)
        labels, cx, cy = kmeans(xs, ys, cx, cy)
        score = sse(xs, ys, labels, cx, cy)
        if best_score is None or score < best_score:
            best_score, best_labels, best_cx, best_cy = score, labels, cx, cy
    return best_labels, best_cx, best_cy


def sse_trace(xs, ys, cx, cy):
    """Steps 2-3 until the centroids stop moving; SSE after each update (as in the figure)."""
    trace = []
    for step in range(300):
        labels = assign(xs, ys, cx, cy)
        new_cx, new_cy = update(xs, ys, labels, cx, cy)
        trace.append(sse(xs, ys, labels, new_cx, new_cy))
        if np.all(new_cx == cx) and np.all(new_cy == cy):
            break
        cx, cy = new_cx, new_cy
    return trace, cx, cy


# ---- helpers ----

def canonical(labels):
    """Labels with cluster numbers relabelled in order of first appearance."""
    order = {}
    out = []
    for l in labels:
        if l not in order:
            order[l] = len(order)
        out.append(order[l])
    return tuple(out)


def two_way_agree(labels, y):
    """Agreement of a 2-cluster labelling with a 0/1 key, either numbering."""
    a = np.mean(labels == y)
    return max(a, 1 - a)


def threshold_agree(labels, values):
    """Best agreement between a 2-cluster labelling and a single threshold on `values`."""
    best = 0.0
    for t in np.unique(values):
        a = two_way_agree(labels, (values > t).astype(int))
        best = max(best, a)
    return best


def main():
    np.random.seed(0)
    brightness, weights, bx, by, init_A, init_B, cx_moved, cy_moved = load_deck()
    print(f"[data] 80 points, duplicate pairs: {80 - len(set(zip(brightness, weights)))}; "
          f"blobs: 400 points, init_A {init_A}, init_B {init_B}")
    zb = (brightness - brightness.mean()) / brightness.std()
    zw = (weights - weights.mean()) / weights.std()

    # the slide's per-point assign and the vectorised assign must agree exactly
    n_checked = 0
    for xs, ys in ((brightness, weights), (zb, zw), (bx, by)):
        for k in (2, 3, 5):
            for _ in range(50):
                cx, cy = init_centroids(xs, ys, k)
                assert np.array_equal(assign(xs, ys, cx, cy), assign_deck(xs, ys, cx, cy))
                n_checked += 1
    print(f"[check] slide assign (per point) == vectorised assign on {n_checked} random inits")
    print(f"[scale] brightness mean {brightness.mean():.2f} std {brightness.std():.2f}; "
          f"weights mean {weights.mean():.2f} std {weights.std():.2f}")
    print(f"[scale] z_brightness[:3] = {zb[:3].round(2).tolist()}, z_weights[:3] = {zw[:3].round(2).tolist()}")

    # single-run k=2 on raw and on standardised data
    for name, xs, ys in [("raw", brightness, weights), ("scaled", zb, zw)]:
        parts, steps, empties, details = Counter(), [], 0, {}
        for _ in range(3000):
            labels, cx, cy, n, empty = kmeans_traced(xs, ys, *init_centroids(xs, ys, 2))
            key = canonical(labels)
            parts[key] += 1
            steps.append(n)
            empties += empty
            if key not in details:
                details[key] = (cx, cy, sse(xs, ys, labels, cx, cy),
                                threshold_agree(labels, weights), threshold_agree(labels, brightness))
        print(f"\n[{name} k=2] distinct final partitions over 3000 runs: {len(parts)}; "
              f"rounds min/median/max = {min(steps)}/{int(np.median(steps))}/{max(steps)}; "
              f"runs with an empty cluster: {empties}")
        for key, cnt in parts.most_common(5):
            cx, cy, s, wt, bt = details[key]
            print(f"   {cnt:5d}x  sizes={(key.count(0), key.count(1))}  SSE={s:.2f}  "
                  f"weight-threshold agree={wt:.3f}  brightness-threshold agree={bt:.3f}  "
                  f"centroids x={np.round(cx, 2).tolist()} y={np.round(cy, 2).tolist()}")

    print("\n[empty clusters, scaled, 5000 single runs per k]")
    for k in range(1, 9):
        empties, steps = 0, []
        for _ in range(5000):
            _, _, _, n, empty = kmeans_traced(zb, zw, *init_centroids(zb, zw, k))
            empties += empty
            steps.append(n)
        print(f"   k={k}: runs with an empty cluster = {empties} ({empties/50:.2f}%), max rounds = {max(steps)}")

    print("\n[elbow, scaled, kmeans_best (n_init=10) per k, 1000 renders]")
    ks = range(1, 9)
    curves = np.array([[sse(zb, zw, *kmeans_best(zb, zw, k)) for k in ks] for _ in range(1000)])
    for i, k in enumerate(ks):
        print(f"   k={k}: min {curves[:, i].min():7.2f}  median {np.median(curves[:, i]):7.2f}  max {curves[:, i].max():7.2f}")
    drops = curves[:, :-1] - curves[:, 1:]
    print(f"   renders where SSE rises somewhere between consecutive k: {np.mean(np.any(drops < 0, axis=1)):.3f}")
    print(f"   renders where the k=1->2 drop is the largest drop: {np.mean(drops[:, 0] > drops[:, 1:].max(axis=1)):.3f}; "
          f"k=1->2 drop min {drops[:, 0].min():.2f}; any later drop max {drops[:, 1:].max():.2f}")

    print("\n[5 blobs, frozen] generated once with default_rng(1), centers (0,0),(4.5,0.5),(9,0),(2,4.5),(7,5), "
          "std 0.6, sizes 140/100/60/60/40, rounded to 1 decimal")
    sizes = [140, 100, 60, 60, 40]
    blob = np.repeat(np.arange(5), sizes)

    def blob_table(labels):
        """5x5 counts: rows = generating blob, columns = k-means cluster."""
        T = np.zeros((5, 5), dtype=int)
        np.add.at(T, (blob, labels), 1)
        return T

    def one_per_blob(labels):
        T = blob_table(labels)
        return bool(np.all(np.count_nonzero(T, axis=0) == 1) and np.all(np.count_nonzero(T, axis=1) == 1))

    results = []
    for s in range(1000):
        np.random.seed(s)
        labels, cx, cy = kmeans(bx, by, *init_centroids(bx, by, 5))
        results.append((sse(bx, by, labels, cx, cy), labels))
    vals = np.array([r[0] for r in results])
    best = vals.min()
    good = vals < best + 0.05
    assert all(one_per_blob(results[i][1]) == bool(good[i]) for i in range(1000))
    print(f"   best SSE {best:.2f} (= one cluster per blob); seeds 0..999 reaching it: {good.sum()}/1000")
    print(f"   restart bar chart, seeds 0..9: {[round(float(v), 1) for v in vals[:10]]}")
    bad = vals[~good]
    print(f"   other answers over 1000 seeds: SSE min {bad.min():.1f}, median {np.median(bad):.1f}, "
          f"max {bad.max():.1f}; min / best = {bad.min() / best:.2f}")

    ab = {}
    for name, init in [("A", init_A), ("B", init_B)]:
        idx = np.array(init)
        labels, cx, cy = kmeans(bx, by, bx[idx], by[idx])
        ab[name] = (labels, cx, cy, sse(bx, by, labels, cx, cy))
        print(f"   {name}: SSE {ab[name][3]:.2f}; rows = blobs (0,0),(4.5,0.5),(9,0),(2,4.5),(7,5), "
              f"cols = clusters\n{blob_table(labels)}")
    print(f"   A / B = {ab['A'][3] / ab['B'][3]:.2f}")

    # the SSE-decrease slide: 4 rounds from a random start, printed with 2 decimals
    ups = 0
    for _ in range(3000):
        cx, cy = init_centroids(bx, by, 5)
        printed = []
        for step in range(1, 5):
            labels = assign(bx, by, cx, cy)
            printed.append(round(sse(bx, by, labels, cx, cy), 2))
            cx, cy = update(bx, by, labels, cx, cy)
            printed.append(round(sse(bx, by, labels, cx, cy), 2))
        ups += sum(b > a for a, b in zip(printed, printed[1:]))
    print(f"   4 rounds from 3000 random starts: printed SSE went up {ups} times")

    # local-minimum figure: A's trace, then the frozen moved centroids
    idx = np.array(init_A)
    trace_stop, cx_stop, cy_stop = sse_trace(bx, by, bx[idx], by[idx])
    assert np.allclose(cx_stop, ab["A"][1]) and np.allclose(cy_stop, ab["A"][2])
    moved = sse(bx, by, assign(bx, by, cx_moved, cy_moved), cx_moved, cy_moved)
    trace_after, _, _ = sse_trace(bx, by, cx_moved, cy_moved)
    print(f"   A trace (SSE after each update): {[round(float(v), 1) for v in trace_stop]}")
    print(f"   frozen moved centroids: SSE right after {moved:.1f}, then {[round(float(v), 1) for v in trace_after]}; "
          f"reaches best: {abs(trace_after[-1] - best) < 0.05}")

    # random restart: evidence for "more restarts reach the best answer more often"
    for n_init, reps in ((1, 2000), (3, 2000), (10, 1000)):
        found = np.mean([sse(bx, by, *kmeans_best(bx, by, 5, n_init=n_init)) < best + 0.05 for _ in range(reps)])
        print(f"   kmeans_best n_init={n_init}: best answer in {found:.3f} of {reps}")

    print("\n[4-point exercise]")
    px, py = np.array([0.0, 0.0, 4.0, 4.0]), np.array([0.0, 2.0, 0.0, 2.0])
    for cx0, cy0 in (([0.0, 0.0], [0.0, 2.0]), ([0.0, 4.0], [0.0, 0.0])):
        labels, cx, cy, n, _ = kmeans_traced(px, py, np.array(cx0), np.array(cy0))
        print(f"   init x={cx0} y={cy0}: labels={labels.tolist()} centroids x={cx.tolist()} y={cy.tolist()} "
              f"SSE={sse(px, py, labels, cx, cy):.1f} rounds={n}")

    # Displayed stand-ins: where the student code is random, the slide shows the output of a
    # hidden twin that replaces the random step with the fixed values below (2026-11-10).
    print("\n[displayed stand-ins]")
    src = DECK.read_text(encoding="utf-8")
    fixed = np.array([6, 48])
    assert "idx = np.array([6, 48])" in src
    labels, cx, cy, n, _ = kmeans_traced(brightness, weights, brightness[fixed], weights[fixed])
    print(f"   steps 1-4 from points {fixed.tolist()}: rounds {n}, sizes {np.bincount(labels).tolist()}, "
          f"weight-threshold agree {threshold_agree(labels, weights):.3f}")
    labels, cx, cy, n, _ = kmeans_traced(zb, zw, zb[fixed], zw[fixed])
    print(f"   standardised retry from points {fixed.tolist()}: rounds {n}, sizes {np.bincount(labels).tolist()}, "
          f"SSE {sse(zb, zw, labels, cx, cy):.2f}")
    np.random.seed(0)
    capture = [round(float(sse(zb, zw, *kmeans_best(zb, zw, k))), 2) for k in range(1, 9)]
    (deck_elbow,) = [ast.literal_eval(m.group(1)) for m in re.finditer(r"^sse_list = (\[\d[^\]]*\])", src, re.M)]
    assert capture == deck_elbow, f"deck elbow values {deck_elbow} != capture {capture}"
    print(f"   elbow, one kmeans_best run captured with np.random.seed(0): {capture} (matches the deck)")

    print("\n[limits demo] numpy-generated circles and moons, k=2, fixed initial points as in the deck")
    rng = np.random.default_rng(42)
    t = rng.uniform(0, 2 * np.pi, 100)
    ring = np.column_stack([np.cos(t), np.sin(t)])
    X_circ = np.vstack([ring, 0.4 * ring]) + rng.normal(0, 0.04, (200, 2))
    t = rng.uniform(0, np.pi, 100)
    X_moon = np.vstack([np.column_stack([np.cos(t), np.sin(t)]),
                        np.column_stack([1 - np.cos(t), 0.5 - np.sin(t)])]) + rng.normal(0, 0.05, (200, 2))
    truth = np.array([0] * 100 + [1] * 100)
    for name, Xe, init in [("circles", X_circ, [0, 45]), ("moons", X_moon, [0, 1])]:
        xs, ys = Xe[:, 0], Xe[:, 1]
        labels, cx, cy = kmeans(xs, ys, xs[init], ys[init])
        lowest = min(sse(xs, ys, *kmeans_best(xs, ys, 2)) for _ in range(100))
        print(f"   {name} from points {init}: SSE {sse(xs, ys, labels, cx, cy):.4f} "
              f"(lowest over 100 kmeans_best runs {lowest:.4f}); sizes={np.bincount(labels).tolist()} "
              f"agreement with true rings/moons={two_way_agree(labels, truth):.3f}")


if __name__ == "__main__":
    main()
