# Generates the frozen values written into dimensionality-pca.qmd, so that
# doc/measured-log.md and the deck's hidden cells are filled from this output
# and never from memory.
#
# The student-visible cells of the deck draw fresh random points on every run
# (no seed). What the slides display (printed output, figures, numbers in the
# text) comes from the values below, generated once here and pasted into
# hidden cells as literals.
#
#   nn_median : median nearest-neighbour distance of 100 uniform points in
#               [0,1]^d, default_rng(0)
#   cv_list   : std/mean of the distances from one query point to 2000
#               uniform points, legacy np.random.seed(42); also prints
#               min / max / difference / ratio as evidence for the wording
#               "the ratio approaches 1, the difference does not shrink"
#   pts_mid   : 60 points of the "central 50%" figure, default_rng(7)
#   pts1d / pts2d : 20 points each of the sparsity figure, np.random.seed(0)
#
# Usage: python tools/measure_dimensionality_pca.py    (from the repo root)

import numpy as np


def literal(name, arr, decimals):
    print(f"{name} = np.array({np.round(arr, decimals).tolist()})")


rng = np.random.default_rng(0)
dims = [1, 2, 3, 5, 10, 20]
nn_median = []
for d in dims:
    P = rng.random((100, d))
    if d == 2:
        # The 2-D sample of this run is the frozen point set `P` of the
        # slides 準備 / 距離を測る (rounded to 3 decimals).
        P2 = np.round(P, 3)
    D = np.sqrt(((P[:, None, :] - P[None, :, :]) ** 2).sum(axis=2))
    np.fill_diagonal(D, np.inf)
    nn_median.append(np.median(D.min(axis=1)))
print("dims =", dims)
print("nn_median =", [round(float(m), 3) for m in nn_median])

# Frozen 2-D points and the numbers the slide 距離を測る prints for them
print("P = np.array([")
for k in range(0, 100, 5):
    print("    " + ", ".join(f"[{x:.3f}, {y:.3f}]" for x, y in P2[k:k + 5]) + ",")
print("])")
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

pts_mid = np.round(np.random.default_rng(7).random((60, 2)), 2)
literal("pts_mid", pts_mid, 2)
inside = ((pts_mid > 0.25) & (pts_mid < 0.75)).all(axis=1)
print(f"# pts_mid: {inside.sum()} of 60 inside the central square")

np.random.seed(0)
literal("pts1d", np.random.rand(20), 2)
literal("pts2d", np.random.rand(20, 2), 2)
