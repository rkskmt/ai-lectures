# Measures every number asserted in knn-curse.qmd and generates the frozen
# values written into the deck, so that doc/measured-log.md and the deck are
# filled from this output and never from memory.
#
# Data (make_data, the same function as in the deck)
#   n points uniform in [0,1]^d; label 1 when the sum of the coordinates is
#   larger than d/2, else 0; each label flipped with probability 0.1.
#
# k-NN in 2-D
#   X_train / y_train / X_test / y_test (100 + 100 points) are one run of
#   make_data with default_rng(seed), coordinates rounded to 3 decimals and
#   the label rule re-applied to the rounded coordinates (flips kept). The
#   seed is the one in 0..199 whose train/test accuracy curves over KS are
#   closest to the mean curves of all 200 seeds, so that the slides show the
#   typical shape and not the noise of one draw. They are written into the
#   deck as literals.
#   x_new (a literal in the deck) is the new point of the comparison slide:
#   the depth-3 decision tree and the vote of its 3 nearest training points
#   must give the same label, with a 2 : 1 vote.
#
# Raising the dimension (student cells unseeded, eval: false; the slides show
# one run with default_rng(0), drawn in the order of the slide's loops)
#   knn_dims  : k-NN (k = 3) accuracy, 100 training / 1000 test points,
#               d = 2, 3, 5, 10, 20
#   nn_median : median distance from each of 100 points to its nearest
#               other point, d = 2, 3, 5, 10, 20
#   more_acc  : k-NN (k = 3) accuracy with 1000 / 10000 / 100000 training
#               points and 1000 test points, d = 2, 5, 10, 20
#
# Curse of dimensionality, figures (unchanged)
#   cv_list   : std/mean of the distances from one query point to 2000
#               uniform points, legacy np.random.seed(42)
#   pts       : 60 points of the "central 50%" figure, default_rng(7)
#   pts1d / pts2d : 20 points each of the sparsity figure, np.random.seed(0)
#
# KD-tree (the deck's build_kdtree / nearest_kdtree: median split, axes in
# turn, leaf size 5, the far side searched only when the split is closer
# than the best distance so far; slides show one run with default_rng(0))
#   kd_count : mean number of distance computations for 100 uniform query
#              points in 2-D, n = 1000 / 10000 / 100000
#   kd_dims  : the same for n = 10000 in 2 / 5 / 10 / 20 dimensions; also
#              prints the median nearest distance and how often the far side
#              of a split had to be searched
#
# Each generated value is compared with the literal in the deck; a mismatch
# stops the script.
#
# Usage: python tools/measure_knn_curse.py    (from the repo root)

import ast
import re
from pathlib import Path

import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier

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


def print_points(name, X):
    print(f"{name} = np.array([")
    for k in range(0, len(X), 5):
        print("    " + ", ".join(f"[{a:.3f}, {b:.3f}]" for a, b in X[k:k + 5]) + ",")
    print("])")


def print_labels(name, y):
    print(f"{name} = np.array([" + ", ".join(map(str, y[:50])) + ",")
    print(" " * (len(name) + 13) + ", ".join(map(str, y[50:])) + "])")


# ---- the deck's functions ----

def make_data(rng, n, d):
    X = rng.random((n, d))
    y = (X.sum(axis=1) > d / 2).astype(int)
    flip = rng.random(n) < 0.1
    y[flip] = 1 - y[flip]
    return X, y


def predict_knn(X_train, y_train, x, k):
    dist = np.sqrt(((X_train - x) ** 2).sum(axis=1))
    nearest = np.argsort(dist)[:k]
    votes = y_train[nearest]
    return int(votes.sum() > k / 2)


def accuracy_knn(X_train, y_train, X, y, k):
    pred = [predict_knn(X_train, y_train, x, k) for x in X]
    return np.mean(np.array(pred) == y)


def nearest_distance(P, i):
    dist = np.sqrt(((P - P[i]) ** 2).sum(axis=1))
    dist[i] = np.inf
    return dist.min()


def build_kdtree(X, idx, depth, leaf_size):
    if len(idx) <= leaf_size:
        return {"points": idx}
    axis = depth % X.shape[1]
    idx = idx[np.argsort(X[idx, axis])]
    mid = len(idx) // 2
    return {"axis": axis,
            "value": X[idx[mid], axis],
            "left": build_kdtree(X, idx[:mid], depth + 1, leaf_size),
            "right": build_kdtree(X, idx[mid:], depth + 1, leaf_size)}


def search_kdtree(node, X, x, best):
    if "points" in node:
        dist = np.sqrt(((X[node["points"]] - x) ** 2).sum(axis=1))
        best["count"] += len(dist)
        j = dist.argmin()
        if dist[j] < best["dist"]:
            best["index"] = node["points"][j]
            best["dist"] = dist[j]
        return
    diff = x[node["axis"]] - node["value"]
    if diff < 0:
        near, far = node["left"], node["right"]
    else:
        near, far = node["right"], node["left"]
    search_kdtree(near, X, x, best)
    best["splits"] += 1                      # tool only: splits met on the way back
    if abs(diff) < best["dist"]:
        best["far"] += 1                     # tool only: far sides searched
        search_kdtree(far, X, x, best)


def nearest_kdtree(tree, X, x):
    best = {"index": -1, "dist": np.inf, "count": 0, "splits": 0, "far": 0}
    search_kdtree(tree, X, x, best)
    return best


def leaves(node):
    if "points" in node:
        return [node["points"]]
    return leaves(node["left"]) + leaves(node["right"])


# ==== k-NN in 2-D: the data ====

print("# ---- k-NN in 2-D ----")
KS = [1, 3, 5, 9, 15, 21, 31, 51, 71]


def frozen_2d(seed):
    """One run of make_data, rounded to 3 decimals, label rule re-applied."""
    rng = np.random.default_rng(seed)
    out = []
    for n in [100, 100]:
        X, y = make_data(rng, n, 2)
        flipped = y != (X.sum(axis=1) > 1)
        X = np.round(X, 3)
        out += [X, ((X.sum(axis=1) > 1) != flipped).astype(int)]
    return out


def curves(X_train, y_train, X_test, y_test):
    out = []
    for X, y in [(X_train, y_train), (X_test, y_test)]:
        order = np.argsort(((X[:, None, :] - X_train[None, :, :]) ** 2).sum(axis=2), axis=1)
        out.append([np.mean((y_train[order[:, :k]].sum(axis=1) > k / 2).astype(int) == y) for k in KS])
    return np.array(out)


all_curves = np.array([curves(*frozen_2d(s)) for s in range(200)])
mean_curve = all_curves.mean(axis=0)
seed = int(((all_curves - mean_curve) ** 2).sum(axis=(1, 2)).argmin())
print(f"# KS = {KS}")
print("# mean over 200 seeds  train " + " ".join(f"{v:.3f}" for v in mean_curve[0]))
print("#                      test  " + " ".join(f"{v:.3f}" for v in mean_curve[1]))
print(f"# chosen seed {seed:<3d}     train " + " ".join(f"{v:.3f}" for v in all_curves[seed][0]))
print("#                      test  " + " ".join(f"{v:.3f}" for v in all_curves[seed][1]))

X_train, y_train, X_test, y_test = frozen_2d(seed)
for name, X, y in [("X_train", X_train, y_train), ("X_test", X_test, y_test)]:
    flipped = np.flatnonzero(y != (X.sum(axis=1) > 1))
    print(f"# {name}: label 1 {y.sum()}, label 0 {len(y) - y.sum()}, flipped {len(flipped)}: {flipped.tolist()}")
print_points("X_train", X_train)
print_labels("y_train", y_train)
print_points("X_test", X_test)
print_labels("y_test", y_test)
check("X_train", X_train, 3)
check("y_train", y_train, 0)
check("X_test", X_test, 3)
check("y_test", y_test, 0)
check("ks", KS, 0)

# ==== k-NN in 2-D: the slides ====

dup = len(X_train) - len(np.unique(X_train, axis=0))
assert dup == 0, "identical training points: k = 1 on the training data is no longer self-evident"
ties = 0
for k in KS:
    for x in np.vstack([X_train, X_test]):
        dist = np.sqrt(((X_train - x) ** 2).sum(axis=1))
        kth = np.sort(dist)[k - 1]
        if np.isclose(kth, np.sort(dist)[k]):
            tied = np.flatnonzero(np.isclose(dist, kth))
            assert len(set(y_train[tied])) == 1, f"k = {k}: tied points {tied} differ in label"
            ties += 1
print(f"# no identical training points; {ties} distance ties at the k-th neighbour over KS, "
      "all between points of one label")

tree_clf = DecisionTreeClassifier(max_depth=3, random_state=0).fit(X_train, y_train)
x_new = np.array(deck_literal("x_new"))
d_new = np.sqrt(((X_train - x_new) ** 2).sum(axis=1))
o_new = np.argsort(d_new)
tree_label = int(tree_clf.predict([x_new])[0])
vote = y_train[o_new[:3]]
print(f"# x_new {x_new.tolist()}: depth-3 tree says {tree_label}; 3 nearest X_train{o_new[:3].tolist()} "
      f"labels {vote.tolist()} at {np.round(d_new[o_new[:3]], 3).tolist()}; "
      f"flipped among them: {[int(i) for i in o_new[:3] if y_train[i] != (X_train[i].sum() > 1)]}")
assert sorted(vote.tolist()) in ([0, 1, 1], [0, 0, 1]) and int(vote.sum() > 1.5) == tree_label, \
    "x_new must get a 2 : 1 vote that agrees with the tree"
print(f"# depth-3 tree: train accuracy {tree_clf.score(X_train, y_train):.3f}, "
      f"test accuracy {tree_clf.score(X_test, y_test):.3f}")

p3 = np.array([predict_knn(X_train, y_train, x, 3) for x in X_test])
print(f"# k = 3: test hits {np.sum(p3 == y_test)} / 100; x_new predicted {predict_knn(X_train, y_train, x_new, 3)}")
print("# k    train  test")
for k in KS:
    print(f"# {k:2d}   {accuracy_knn(X_train, y_train, X_train, y_train, k):.3f}  "
          f"{accuracy_knn(X_train, y_train, X_test, y_test, k):.3f}")
for k in [1, 31]:
    p = np.array([predict_knn(X_train, y_train, x, k) for x in X_test])
    print(f"# k = {k}: test hits {np.sum(p == y_test)} / 100")
print(f"# best possible on the test data (labels that follow the rule): "
      f"{np.mean(y_test == (X_test.sum(axis=1) > 1)):.3f}")

for algorithm in ["auto", "kd_tree"]:
    sk = KNeighborsClassifier(n_neighbors=3, algorithm=algorithm).fit(X_train, y_train)
    print(f"# KNeighborsClassifier(n_neighbors=3, algorithm={algorithm!r}): test hits "
          f"{np.sum(sk.predict(X_test) == y_test)} / 100, same as predict_knn: "
          f"{np.array_equal(sk.predict(X_test), p3)}")

nn0 = nearest_distance(X_train, 0)
nn_all = [nearest_distance(X_train, i) for i in range(len(X_train))]
j0 = np.argsort(np.sqrt(((X_train - X_train[0]) ** 2).sum(axis=1)))[1]
print(f"# X_train point 0 {X_train[0].tolist()}: nearest point {j0} at {nn0:.3f}; "
      f"median over the 100 points {np.median(nn_all):.3f} (min {min(nn_all):.3f}, max {max(nn_all):.3f})")

Q = np.array([[3.0, 4.0], [1.0, 3.0], [3.0, 1.0], [6.0, 7.0], [7.0, 6.0]])   # A, B, C, D, E
q_label = np.array([0, 1, 1, 0, 0])
q_new = np.array([3.0, 3.0])
print(f"# exercise: distances A-E {np.sqrt(((Q - q_new) ** 2).sum(axis=1)).tolist()}, "
      f"predictions k = 1, 3, 5: {[predict_knn(Q, q_label, q_new, k) for k in [1, 3, 5]]}")


# ==== raising the dimension ====

print("# ---- raising the dimension ----")
rng = np.random.default_rng(0)
knn_dims, best = [], []
for d in [2, 3, 5, 10, 20]:
    Xtr, ytr = make_data(rng, 100, d)
    Xte, yte = make_data(rng, 1000, d)
    knn_dims.append(accuracy_knn(Xtr, ytr, Xte, yte, 3))
    best.append(np.mean(yte == (Xte.sum(axis=1) > d / 2)))
print("knn_dims =", [round(float(a), 3) for a in knn_dims])
print("# best possible on each test set:", [round(float(b), 3) for b in best])
check("knn_dims", knn_dims, 3)

rng = np.random.default_rng(0)
nn_median = []
for d in [2, 3, 5, 10, 20]:
    P, label = make_data(rng, 100, d)
    nn_median.append(np.median([nearest_distance(P, i) for i in range(len(P))]))
print("nn_median =", [round(float(m), 3) for m in nn_median])
check("nn_median", nn_median, 3)

rng = np.random.default_rng(0)
more_acc, best = [], []
for n in [1000, 10000, 100000]:
    row = []
    for d in [2, 5, 10, 20]:
        Xtr, ytr = make_data(rng, n, d)
        Xte, yte = make_data(rng, 1000, d)
        row.append(accuracy_knn(Xtr, ytr, Xte, yte, 3))
        best.append(np.mean(yte == (Xte.sum(axis=1) > d / 2)))
    more_acc.append(row)
print("more_acc =", [[round(float(a), 3) for a in row] for row in more_acc])
print(f"# best possible on these test sets: {min(best):.3f} to {max(best):.3f}")
check("more_acc", more_acc, 3)


# ==== curse of dimensionality: figures ====

print("# ---- curse of dimensionality: figures ----")
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
print("cv_list =", [round(float(c), 3) for c in cv_list])
check("cv_list", cv_list, 3)

pts_mid = np.round(np.random.default_rng(7).random((60, 2)), 2)
literal("pts", pts_mid, 2)
check("pts", pts_mid, 2)

np.random.seed(0)
pts1d, pts2d = np.random.rand(20), np.random.rand(20, 2)
literal("pts1d", pts1d, 2)
literal("pts2d", pts2d, 2)
check("pts1d", pts1d, 2)
check("pts2d", pts2d, 2)


# ==== KD-tree ====

print("# ---- KD-tree ----")
tree = build_kdtree(X_train, np.arange(len(X_train)), 0, 5)
lv = leaves(tree)
print(f"# tree on X_train (leaf size 5): {len(lv)} leaves of {sorted({len(p) for p in lv})} points; "
      f"first split feature {tree['axis'] + 1} = {tree['value']}")
b = nearest_kdtree(tree, X_train, x_new)
assert b["index"] == o_new[0], "the KD-tree must find the same nearest point as the full search"
print(f"# x_new: KD-tree finds X_train[{b['index']}] at {b['dist']:.3f} after {b['count']} distance computations "
      f"(far side searched {b['far']} of {b['splits']} splits)")

rng = np.random.default_rng(0)
kd_count = []
for n in [1000, 10000, 100000]:
    X = rng.random((n, 2))
    tree = build_kdtree(X, np.arange(n), 0, 5)
    kd_count.append(np.mean([nearest_kdtree(tree, X, q)["count"] for q in rng.random((100, 2))]))
print("kd_count =", [round(float(c), 1) for c in kd_count])
check("kd_count", kd_count, 1)

rng = np.random.default_rng(0)
kd_dims = []
n = 10000
for d in [2, 5, 10, 20]:
    X = rng.random((n, d))
    tree = build_kdtree(X, np.arange(n), 0, 5)
    found = [nearest_kdtree(tree, X, q) for q in rng.random((100, d))]
    kd_dims.append(np.mean([f["count"] for f in found]))
    far = sum(f["far"] for f in found) / sum(f["splits"] for f in found)
    print(f"# {d:2d}-D, n = {n}: mean count {kd_dims[-1]:.1f} ({kd_dims[-1] / n:.3f} of n), "
          f"median nearest distance {np.median([f['dist'] for f in found]):.3f}, "
          f"far side searched at {far:.3f} of the splits")
print("kd_dims =", [round(float(c), 1) for c in kd_dims])
check("kd_dims", kd_dims, 1)


# ==== checkpoint: the fish of the evaluation deck ====
#   The checkpoint asks the student to split the 120 fish at random (96 / 24),
#   compare a depth-3 decision tree with k-NN (k = 3), and redo k-NN after
#   standardizing with the training mean and std. Its answer states
#   properties only; the numbers below are the evidence over 1000 random
#   splits (default_rng(0).permutation), not slide content.

print("# ---- checkpoint: fish ----")
EVAL_SRC = (ROOT / "classification-evaluation.qmd").read_text(encoding="utf-8")
fish = {}
for name in ["salmon_weights", "salmon_brightness", "seabass_weights", "seabass_brightness"]:
    fish[name] = np.array(deck_literal(name))
    m = re.search(r"^" + name + r"\s*=\s*np\.array\((\[.*?\])\)", EVAL_SRC, re.S | re.M)
    assert np.array_equal(fish[name], np.array(ast.literal_eval(m.group(1)))), \
        f"{name}: the checkpoint's fish differ from classification-evaluation.qmd"
print("# the checkpoint's fish are the 120 fish of classification-evaluation.qmd")
Xf = np.array([[fish["salmon_brightness"][i], fish["salmon_weights"][i]] for i in range(60)]
              + [[fish["seabass_brightness"][i], fish["seabass_weights"][i]] for i in range(60)])
yf = np.array([1] * 60 + [0] * 60)
print(f"# brightness {Xf[:, 0].min()} to {Xf[:, 0].max()} (std {Xf[:, 0].std():.2f}), "
      f"weight {Xf[:, 1].min():.0f} to {Xf[:, 1].max():.0f} g (std {Xf[:, 1].std():.1f} g)")
rng = np.random.default_rng(0)
acc_tree, acc_raw, acc_std, same_tree = [], [], [], 0
for _ in range(1000):
    idx = rng.permutation(120)
    Xtr, ytr, Xte, yte = Xf[idx[:96]], yf[idx[:96]], Xf[idx[96:]], yf[idx[96:]]
    mean, std = Xtr.mean(axis=0), Xtr.std(axis=0)
    t_raw = DecisionTreeClassifier(max_depth=3, random_state=0).fit(Xtr, ytr)
    t_std = DecisionTreeClassifier(max_depth=3, random_state=0).fit((Xtr - mean) / std, ytr)
    same_tree += np.array_equal(t_raw.predict(Xte), t_std.predict((Xte - mean) / std))
    acc_tree.append(np.mean(t_raw.predict(Xte) == yte))
    acc_raw.append(accuracy_knn(Xtr, ytr, Xte, yte, 3))
    acc_std.append(accuracy_knn((Xtr - mean) / std, ytr, (Xte - mean) / std, yte, 3))
acc_raw, acc_std = np.array(acc_raw), np.array(acc_std)
print(f"# 1000 random 96/24 splits, mean test accuracy: tree (depth 3) {np.mean(acc_tree):.3f}, "
      f"k-NN k = 3 raw {acc_raw.mean():.3f}, standardized {acc_std.mean():.3f}")
print(f"#   standardized better {np.sum(acc_std > acc_raw)}, worse {np.sum(acc_std < acc_raw)}, "
      f"equal {np.sum(acc_std == acc_raw)}; tree predictions identical raw vs standardized {same_tree} / 1000")
