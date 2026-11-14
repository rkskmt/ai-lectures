# Checks the point layout of the practice problem of knn-curse.qmd
# (練習問題：箱に分けて、近い 3 点を探す): 10 labelled points on a 16 x 16 grid and the new point N.
#
# The layout was picked from a random search over integer layouts with these conditions, all of
# which evaluate() enforces or reports:
#   - quadtree (cut at the midpoints, split above 3 points, at most 2 levels): no point on a cut line
#   - KD-tree (the deck's build_kdtree, leaf size 3): the median point is the only point on its line
#   - the 3 nearest points of N are unique (no tie between the 3rd and the 4th)
#   - by-hand search (box of N, one box up while fewer than 3 points, then every box the circle of
#     radius r reaches): the first circle already settles which boxes are measured, and for the
#     KD-tree it measures the same points as the deck's search_kdtree extended to 3 nearest points
#
# Usage: python tools/design_knn_exercise.py    (from the repo root)
import numpy as np

SIZE, K, LEAF = 16, 3, 3
COORDS = [c for c in range(1, 16) if c != 8]


def quad_leaves(P, idx, lo, hi, depth, out):
    """Leaves (lo, hi, idx, parent_id); returns False when the layout is unusable."""
    if len(idx) <= LEAF:
        out.append((lo, hi, idx))
        return True
    if depth == 2:
        return False
    mid = (lo + hi) / 2
    if np.any(P[idx] == mid):                       # a point on a cut line
        return False
    for cx in (0, 1):
        for cy in (0, 1):
            clo = np.array([mid[0] if cx else lo[0], mid[1] if cy else lo[1]])
            chi = np.array([hi[0] if cx else mid[0], hi[1] if cy else mid[1]])
            inside = idx[np.all((P[idx] > clo) & (P[idx] < chi), axis=1)]
            if not quad_leaves(P, inside, clo, chi, depth + 1, out):
                return False
    return True


def kd_build(P, idx, depth, lo, hi):
    if len(idx) <= LEAF:
        return {"points": idx, "lo": lo, "hi": hi}
    a = depth % 2
    idx = idx[np.argsort(P[idx, a], kind="stable")]
    m = len(idx) // 2
    if P[idx[m - 1], a] == P[idx[m], a]:
        return None                                  # tie at the split: ambiguous by hand
    v = P[idx[m], a]
    if np.sum(P[idx, a] == v) != 1:
        return None                                  # only the median point may lie on the line
    hl, lr = hi.copy(), lo.copy()
    hl[a], lr[a] = v, v
    L, R = kd_build(P, idx[:m], depth + 1, lo, hl), kd_build(P, idx[m:], depth + 1, lr, hi)
    if L is None or R is None:
        return None
    return {"axis": a, "value": v, "left": L, "right": R, "lo": lo, "hi": hi}


def kd_leaves(node, out):
    if "points" in node:
        out.append((node["lo"], node["hi"], node["points"]))
    else:
        kd_leaves(node["left"], out); kd_leaves(node["right"], out)


def box_d2(lo, hi, q):
    return float((np.maximum(np.maximum(lo - q, q - hi), 0) ** 2).sum())


def hand_search(P, q, home_chain, leaves):
    """home_chain: point index arrays of the home box, its parent, grandparent, ...
    Rule: measure the home box; while fewer than K points, go one box up; then measure every leaf
    the circle of radius r (K-th nearest so far) reaches, nearest leaf first."""
    measured = set()
    steps = 0
    for idx in home_chain:
        measured |= set(int(i) for i in idx)
        if len(measured) >= K:
            break
        steps += 1
    def r2():
        return sorted(float(((P[i] - q) ** 2).sum()) for i in measured)[K - 1]
    r0 = r2()
    first = set(measured)
    for lo, hi, idx in leaves:
        if len(idx) and box_d2(lo, hi, q) <= r0:
            first |= set(int(i) for i in idx)
    extra = 0
    while True:
        cand = [(box_d2(lo, hi, q), n) for n, (lo, hi, idx) in enumerate(leaves)
                if len(idx) and not set(int(i) for i in idx) <= measured]
        cand = [c for c in cand if c[0] < r2()]
        if not cand:
            break
        if any(c[0] == r2() for c in cand):
            return None
        n = min(cand)[1]
        measured |= set(int(i) for i in leaves[n][2]); extra += 1
    # tie check: a leaf exactly touching the final circle
    for lo, hi, idx in leaves:
        if len(idx) and not set(int(i) for i in idx) <= measured and box_d2(lo, hi, q) == r2():
            return None
    if first != measured:
        return None                                  # the first circle must already give the final answer
    return measured, steps, extra


def kd_deck_search(node, P, q, best):
    """The deck's search_kdtree extended to K nearest (r = K-th nearest distance so far)."""
    if "points" in node:
        for i in node["points"]:
            best["measured"].add(int(i))
            best["d2"].append(float(((P[i] - q) ** 2).sum()))
        best["d2"].sort()
        return
    diff = q[node["axis"]] - node["value"]
    near, far = (node["left"], node["right"]) if diff < 0 else (node["right"], node["left"])
    kd_deck_search(near, P, q, best)
    if len(best["d2"]) < K or diff * diff < best["d2"][K - 1]:
        kd_deck_search(far, P, q, best)


def kd_chain(node, q, chain):
    if "points" in node:
        chain.append(node["points"]); return node["points"]
    diff = q[node["axis"]] - node["value"]
    if diff == 0:
        raise ValueError
    sub = kd_chain(node["left"] if diff < 0 else node["right"], q, chain)
    allp = np.concatenate([l[2] for l in (lambda o: (kd_leaves(node, o), o)[1])([])])
    chain.append(allp)
    return allp


def quad_chain(P, q, leaves):
    home = [n for n, (lo, hi, idx) in enumerate(leaves) if np.all((q > lo) & (q < hi))]
    if len(home) != 1:
        return None
    lo, hi, idx = leaves[home[0]]
    chain = [idx]
    size = hi[0] - lo[0]
    while size < SIZE:
        size *= 2
        plo = np.floor(lo / size) * size
        chain.append(np.array([i for i in range(len(P)) if np.all((P[i] > plo) & (P[i] < plo + size))]))
        lo = plo
    return chain


def evaluate(P, y, q):
    ql = []
    if not quad_leaves(P, np.arange(len(P)), np.zeros(2), np.full(2, float(SIZE)), 0, ql):
        return None
    tree = kd_build(P, np.arange(len(P)), 0, np.zeros(2), np.full(2, float(SIZE)))
    if tree is None:
        return None
    d2 = ((P - q) ** 2).sum(axis=1)
    order = np.argsort(d2, kind="stable")
    if d2[order[0]] == 0 or d2[order[K - 1]] == d2[order[K]]:
        return None
    qc = quad_chain(P, q, ql)
    if qc is None:
        return None
    try:
        kc = []; kd_chain(tree, q, kc)
    except ValueError:
        return None
    kl = []; kd_leaves(tree, kl)
    hq, hk = hand_search(P, q, qc, ql), hand_search(P, q, kc, kl)
    if hq is None or hk is None:
        return None
    best = {"measured": set(), "d2": []}
    kd_deck_search(tree, P, q, best)
    if best["measured"] != hk[0]:
        return None
    nn = set(int(i) for i in order[:K])
    assert nn <= hq[0] and nn <= hk[0]
    votes = int(y[order[:K]].sum())
    return {"quad_sizes": sorted(len(l[2]) for l in ql), "kd_sizes": sorted(len(l[2]) for l in kl),
            "quad": hq, "kd": hk, "votes": votes, "nn": order[:K].tolist(),
            "quad_home": len(qc[0]), "kd_home": len(kc[0])}


if __name__ == "__main__":
    names = list("ABCDEFGHIJ")
    P = np.array([[3, 15], [6, 3], [6, 9], [6, 13], [7, 10], [9, 14], [11, 13], [12, 3], [12, 7], [13, 14]], dtype=float)
    y = np.array([1, 0, 0, 0, 1, 1, 1, 0, 1, 1])
    q = np.array([5.0, 13.0])
    r = evaluate(P, y, q)
    assert r is not None
    d2 = ((P - q) ** 2).sum(axis=1)
    print("quadtree: points per box", r["quad_sizes"], "| points in the box of N:", r["quad_home"])
    print("KD-tree : points per box", r["kd_sizes"], "| points in the box of N:", r["kd_home"])
    print("3 nearest:", [(names[i], int(d2[i])) for i in r["nn"]], "(name, squared distance) | votes for label 1:", r["votes"])
    print("quadtree measures", sorted(names[i] for i in r["quad"][0]), len(r["quad"][0]), "points")
    print("KD-tree  measures", sorted(names[i] for i in r["kd"][0]), len(r["kd"][0]), "points")
    print("k = 1 predicts", int(y[r["nn"][0]]), "| k = 3 predicts", int(r["votes"] > 1.5))
