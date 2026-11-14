# Measures every number asserted in knn-curse.qmd and generates the frozen
# values written into its hidden cells, so that doc/measured-log.md and the
# deck are filled from this output and never from memory.
#
# k-NN on the fish
#   The 120 fish and the frozen order `idx` are read out of the .qmd. `idx` is
#   np.random.default_rng(0).permutation(120): the student cell shuffles
#   without a seed, the hidden display twin uses this order. Everything is
#   computed with the deck's predict_knn (argsort of the Euclidean distances,
#   majority vote), with the mean and std of the 96 training fish.
#
# Curse of dimensionality
#   The student cells draw fresh random points on every run (no seed). What
#   the slides display comes from the values below, generated once here and
#   pasted into hidden cells as literals:
#     nn_median : median nearest-neighbour distance of 100 uniform points in
#                 [0,1]^d, default_rng(0). Its 2-D draw, rounded to 3
#                 decimals, is the frozen point set P.
#     cv_list   : std/mean of the distances from one query point to 2000
#                 uniform points, legacy np.random.seed(42); also prints
#                 min / max / difference / ratio as evidence for the wording
#                 "the ratio approaches 1, the difference does not shrink"
#     pts       : 60 points of the "central 50%" figure, default_rng(7)
#     pts1d / pts2d : 20 points each of the sparsity figure, np.random.seed(0)
#     nn_hit    : nearest-neighbour hit rate on 100 points with the label
#                 "sum of coordinates > d/2", default_rng(0)
#     more_hit  : the same on n = 1000 / 10000 / 100000 points (the first 1000
#                 predicted, the neighbour searched among all n),
#                 default_rng(0) drawn in the order of the slide's loops
#   Each generated value is compared with the literal in the deck; a mismatch
#   stops the script.
#
# Usage: python tools/measure_knn_curse.py    (from the repo root)

import ast
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "knn-curse.qmd"
SRC = DECK.read_text(encoding="utf-8")


def deck_literal(name):
    """The non-empty literal assigned to `name` in the deck (`name = [...]` or
    `name = np.array([...])`). Every non-empty assignment must agree."""
    found = []
    for m in re.finditer(r"^" + name + r"\s*=\s*(?:np\.array\()?\[", SRC, re.M):
        start = m.end() - 1
        depth = 0
        for end in range(start, len(SRC)):
            depth += {"[": 1, "]": -1}.get(SRC[end], 0)
            if depth == 0:
                break
        value = ast.literal_eval(SRC[start:end + 1])
        if value:
            found.append(value)
    assert found, f"{name}: no literal in {DECK.name}"
    assert all(v == found[0] for v in found), f"{name}: the deck has differing copies"
    return found[0]


def check(name, generated, decimals):
    """Stop unless the deck's literal equals the generated value at the
    precision the deck writes it with."""
    deck = np.array(deck_literal(name), dtype=float)
    gen = np.round(np.asarray(generated, dtype=float), decimals)
    assert deck.shape == gen.shape and np.allclose(deck, gen, atol=1e-9), \
        f"{name}: deck {deck.tolist()} != generated {gen.tolist()}"
    print(f"# {name}: deck literal matches")


def literal(name, arr, decimals):
    print(f"{name} = np.array({np.round(arr, decimals).tolist()})")


# ---- the deck's functions ----

def predict_knn(Z_train, y_train, z, k):
    dist = np.sqrt(((Z_train - z) ** 2).sum(axis=1))
    nearest = np.argsort(dist)[:k]
    votes = y_train[nearest]
    return int(votes.sum() > k / 2)


def predictions(Z_train, y_train, Z, k):
    return np.array([predict_knn(Z_train, y_train, z, k) for z in Z])


def nearest_index(P, i):
    dist = np.sqrt(((P - P[i]) ** 2).sum(axis=1))
    dist[i] = np.inf
    return dist.argmin()


def nn_hits(P, label, count):
    return np.array([label[nearest_index(P, i)] == label[i] for i in range(count)])


# ==== k-NN on the fish ====

print("# ---- k-NN on the fish ----")
salmon_weights = np.array(deck_literal("salmon_weights"))
salmon_brightness = np.array(deck_literal("salmon_brightness"))
seabass_weights = np.array(deck_literal("seabass_weights"))
seabass_brightness = np.array(deck_literal("seabass_brightness"))
X = np.array([[salmon_brightness[i], salmon_weights[i]] for i in range(60)]
             + [[seabass_brightness[i], seabass_weights[i]] for i in range(60)])
y = np.array([1] * 60 + [0] * 60)

check("idx", np.random.default_rng(0).permutation(120), 0)
idx = np.array(deck_literal("idx"))
X_train, y_train = X[idx[:96]], y[idx[:96]]
X_test, y_test = X[idx[96:]], y[idx[96:]]
mean, std = X_train.mean(axis=0), X_train.std(axis=0)
Z_train = (X_train - mean) / std
Z_test = (X_test - mean) / std
print(f"# train {len(y_train)} fish ({y_train.sum()} Salmon), test {len(y_test)} fish ({y_test.sum()} Salmon)")
print(f"# train std: brightness {std[0]:.2f}, weight {std[1]:.1f} g")
u, inv, cnt = np.unique(X_train, axis=0, return_inverse=True, return_counts=True)
for g in np.flatnonzero(cnt > 1):
    same = np.flatnonzero(inv.ravel() == g)
    print(f"# identical training fish {same.tolist()} (original rows {idx[same].tolist()}): "
          f"{X_train[same[0]].tolist()}, labels {y_train[same].tolist()}")

# A distance tie at the k-th neighbour leaves the vote to the order argsort
# returns. It is harmless only when every tied fish has the same label.
ks = deck_literal("ks")
ties = 0
for k in ks:
    for z in np.vstack([Z_train, Z_test]):
        dist = np.sqrt(((Z_train - z) ** 2).sum(axis=1))
        kth = np.sort(dist)[k - 1]
        if np.isclose(kth, np.sort(dist)[k]):
            tied = np.flatnonzero(np.isclose(dist, kth))
            assert len(set(y_train[tied])) == 1, f"k = {k}: tied fish {tied} differ in label"
            ties += 1
print(f"# {ties} distance ties at the k-th neighbour over k = {ks}, all between fish of one label")

p1 = predictions(Z_train, y_train, Z_test, 1)
print(f"# k = 1: test hits {np.sum(p1 == y_test)} / 24, Accuracy {np.mean(p1 == y_test):.3f}")
d4 = np.sqrt(((Z_train - Z_test[4]) ** 2).sum(axis=1))
o4 = np.argsort(d4)
print(f"# test fish 4: true {y_test[4]} (1=Salmon, 0=Sea bass), nearest training fish {y_train[o4[0]]}, "
      f"5 nearest {y_train[o4[:5]].tolist()} (Salmon {y_train[o4[:5]].sum()}, Sea bass {5 - y_train[o4[:5]].sum()})")
p5 = predictions(Z_train, y_train, Z_test, 5)
print(f"# k = 5: test hits {np.sum(p5 == y_test)} / 24; fish 4 predicted {p5[4]}")
print(f"#   right at k = 1 only: {np.flatnonzero((p1 == y_test) & (p5 != y_test)).tolist()}, "
      f"right at k = 5 only: {np.flatnonzero((p1 != y_test) & (p5 == y_test)).tolist()} (test fish numbers)")
print("# k    train  test")
for k in ks:
    tr = np.mean(predictions(Z_train, y_train, Z_train, k) == y_train)
    te = np.mean(predictions(Z_train, y_train, Z_test, k) == y_test)
    print(f"# {k:2d}   {tr:.3f}  {te:.3f}")
p31 = predictions(Z_train, y_train, Z_test, 31)
print(f"# k = 31: test hits {np.sum(p31 == y_test)} / 24")
for k in [1, 5]:
    praw = predictions(X_train, y_train, X_test, k)
    print(f"# without standardization, k = {k}: test hits {np.sum(praw == y_test)} / 24")

from sklearn.neighbors import KNeighborsClassifier  # noqa: E402  (only for the (参考) slide)
sk = KNeighborsClassifier(n_neighbors=5).fit(Z_train, y_train).predict(Z_test)
print(f"# KNeighborsClassifier(n_neighbors=5): test hits {np.sum(sk == y_test)} / 24, "
      f"same predictions as predict_knn: {np.array_equal(sk, p5)}")

Q = np.array([[3.0, 4.0], [1.0, 3.0], [3.0, 1.0], [6.0, 7.0], [7.0, 6.0]])   # A, B, C, D, E
q_label = np.array([0, 1, 1, 0, 0])
q_new = np.array([3.0, 3.0])
print(f"# exercise: distances A-E {np.sqrt(((Q - q_new) ** 2).sum(axis=1)).tolist()}, "
      f"predictions k = 1, 3, 5: {[predict_knn(Q, q_label, q_new, k) for k in [1, 3, 5]]}")


# ==== curse of dimensionality ====

print("# ---- curse of dimensionality ----")
rng = np.random.default_rng(0)
dims = [1, 2, 3, 5, 10, 20]
nn_median = []
for d in dims:
    P = rng.random((100, d))
    if d == 2:
        # The 2-D sample of this run is the frozen point set `P` of the
        # slides 準備 / 距離を測る / ばらまいた点で、最近傍法を試す
        # (rounded to 3 decimals).
        P2 = np.round(P, 3)
    D = np.sqrt(((P[:, None, :] - P[None, :, :]) ** 2).sum(axis=2))
    np.fill_diagonal(D, np.inf)
    nn_median.append(np.median(D.min(axis=1)))
print("dims =", dims)
print("nn_median =", [round(float(m), 3) for m in nn_median])
check("nn_median", nn_median, 3)

# Frozen 2-D points and the numbers the slide 距離を測る prints for them
print("P = np.array([")
for k in range(0, 100, 5):
    print("    " + ", ".join(f"[{x:.3f}, {y:.3f}]" for x, y in P2[k:k + 5]) + ",")
print("])")
check("P", P2, 3)
D2 = np.sqrt(((P2[:, None, :] - P2[None, :, :]) ** 2).sum(axis=2))
np.fill_diagonal(D2, np.inf)
nn2 = D2.min(axis=1)
for i in range(5):
    print(f"# P point {i}: nearest is point {D2[i].argmin()}, "
          f"distance {nn2[i]:.3f}, coords {P2[i]}")
print(f"# P: median nearest distance {np.median(nn2):.3f}, "
      f"min {nn2.min():.3f}, max {nn2.max():.3f}")

np.random.seed(42)
dims = [1, 2, 3, 5, 10, 20, 50, 100]
cv_list = []
for d in dims:
    pts = np.random.rand(2000, d)
    query = np.random.rand(d)
    dists = np.sqrt(((pts - query) ** 2).sum(axis=1))
    cv_list.append(dists.std() / dists.mean())
    print(f"# d={d:3d}: min {dists.min():.3f}  max {dists.max():.3f}  "
          f"diff {dists.max() - dists.min():.3f}  "
          f"max/min {dists.max() / dists.min():.2f}  "
          f"cv {cv_list[-1]:.3f}")
print("dims =", dims)
print("cv_list =", [round(float(c), 3) for c in cv_list])
check("cv_list", cv_list, 3)

pts_mid = np.round(np.random.default_rng(7).random((60, 2)), 2)
literal("pts", pts_mid, 2)
check("pts", pts_mid, 2)
inside = ((pts_mid > 0.25) & (pts_mid < 0.75)).all(axis=1)
print(f"# pts: {inside.sum()} of 60 inside the central square")

np.random.seed(0)
pts1d, pts2d = np.random.rand(20), np.random.rand(20, 2)
literal("pts1d", pts1d, 2)
literal("pts2d", pts2d, 2)
check("pts1d", pts1d, 2)
check("pts2d", pts2d, 2)

# Nearest-neighbour method on the frozen P (the slide ばらまいた点で、最近傍法を試す)
label = P2.sum(axis=1) > 1
hit = nn_hits(P2, label, 100)
gap = np.abs(P2.sum(axis=1) - 1)          # how far off the boundary x + y = 1
rank = np.argsort(np.argsort(gap))         # 0 = the point closest to the boundary
print(f"# nearest-neighbour method on P (label x + y > 1): {hit.sum()} / 100 hit")
print(f"#   missed points {np.flatnonzero(~hit).tolist()}: |x + y - 1| "
      f"{np.round(gap[~hit], 3).tolist()}, closeness rank among 100 {rank[~hit].tolist()}")
print(f"#   |x + y - 1| over all 100 points: median {np.median(gap):.3f}")

# nn_hit: the loop of the slide 質問：次元を増やすと、最近傍法は当たる？
rng = np.random.default_rng(0)
nn_hit = []
for d in [1, 2, 3, 5, 10, 20]:
    P = rng.random((100, d))
    nn_hit.append(nn_hits(P, P.sum(axis=1) > d / 2, 100).mean())
print("nn_hit =", [round(float(h), 2) for h in nn_hit])
check("nn_hit", nn_hit, 2)

# more_hit: the loop of the slide 点を 1000 倍に増やしても、追いつかない
rng = np.random.default_rng(0)
more_hit = []
for n in [1000, 10000, 100000]:
    row = []
    for d in [2, 5, 10, 20]:
        P = rng.random((n, d))
        row.append(nn_hits(P, P.sum(axis=1) > d / 2, 1000).mean())
    more_hit.append(row)
print("more_hit =", [[round(float(h), 2) for h in row] for row in more_hit])
check("more_hit", more_hit, 2)
