# Measures every number asserted in the RANSAC section of linear-regression.qmd
# with the deck's own code (2-point RANSAC + least-squares refit), so that
# doc/measured-log.md can be written from this output and never from memory.
#
#   data : the 80 fish defined in the deck (weights listed in the .qmd, lengths
#          synthesised with default_rng(42) exactly as the deck does)
#   bad  : the deck multiplies the weight of the two largest fish (indices BAD)
#          by 10: "an extra zero typed on two slips"
#   runs : the deck's RANSAC cell is unseeded, so every claim is checked over
#          many seeds here
#
# Usage: python tools/measure_linear_regression_ransac.py   (from the repo root)

import re
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.linear_model import LinearRegression, RANSACRegressor

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "linear-regression.qmd"

BAD = [3, 6]                           # the two heaviest fish, weight x10 (extra zero)
BAD20 = list(range(0, 80, 4))          # Tweak row: 20 slips with an extra zero
THRESHOLD = 300                        # grams; Tweak rows try 50 and 30000
N_TRIALS = 200                         # Tweak row tries 3
SEEDS = 300


def load_fish():
    src = DECK.read_text(encoding="utf-8")

    def arr(name):
        m = re.search(name + r"\s*=\s*np\.array\(\[(.*?)\]", src, re.S)
        return np.array([float(v) for v in re.findall(r"[-\d.]+", m.group(1))])

    weights = np.concatenate([arr("salmon_weights"), arr("seabass_weights")]).astype(float)
    assert len(weights) == 80
    rng = np.random.default_rng(42)
    lengths = np.round(np.cbrt(weights) * 4.5 + rng.normal(0, 1.0, len(weights)), 1)
    return lengths, weights


def with_typos(weights, bad):
    w = weights.copy()
    w[bad] *= 10
    return w


def ls_fit(x, t):
    reg = LinearRegression().fit(x.reshape(-1, 1), t)
    return reg.coef_[0], reg.intercept_


# ---- the deck's RANSAC (same code as the slide) ----

def ransac_line(x, t, threshold, n_trials=200):
    best_count = 0
    for trial in range(n_trials):
        i, j = np.random.choice(len(x), 2, replace=False)
        if x[i] == x[j]:
            continue
        a = (t[j] - t[i]) / (x[j] - x[i])
        b = t[i] - a * x[i]
        inliers = np.abs(a * x + b - t) < threshold
        if inliers.sum() > best_count:
            best_count, best_inliers = inliers.sum(), inliers
    a, b = ls_fit(x[best_inliers], t[best_inliers])
    return a, b, best_inliers


def ransac_stats(label, x, t, bad, threshold, n_trials, seeds=SEEDS):
    good = np.ones(len(x), bool)
    good[bad] = False
    counts, slopes, excluded_all, exact = [], [], 0, 0
    for s in range(seeds):
        np.random.seed(s)
        a, b, inl = ransac_line(x, t, threshold, n_trials)
        counts.append(int(inl.sum()))
        slopes.append(a)
        excluded_all += int(not inl[bad].any())
        exact += int(np.array_equal(inl, good))
    print(f"   [{label}] threshold={threshold} n_trials={n_trials}, {seeds} seeds")
    print(f"      inlier count: {dict(sorted(Counter(counts).items()))}")
    print(f"      slope: min {min(slopes):.2f}  max {max(slopes):.2f}  mean {np.mean(slopes):.2f}")
    print(f"      all {len(bad)} typos excluded: {excluded_all}/{seeds};  exactly the {len(x) - len(bad)} correct slips kept: {exact}/{seeds}")
    np.random.seed()


def main():
    lengths, weights = load_fish()
    a0, b0 = ls_fit(lengths, weights)
    res = weights - (a0 * lengths + b0)
    print("[clean fit, 80 fish]")
    print(f"   a={a0:.2f} g/cm  b={b0:.1f}  residual std={res.std():.1f}  max|res|={np.abs(res).max():.1f}")
    print(f"   duplicated lengths among the 80: {80 - len(np.unique(lengths))} (two-point sampling must skip equal x)")
    order = np.argsort(lengths)
    print(f"   longest fish: idx {order[-3:][::-1].tolist()} lengths {lengths[order[-3:][::-1]].tolist()} weights {weights[order[-3:][::-1]].tolist()}")
    mid = np.argsort(np.abs(lengths - lengths.mean()))[:4]
    print(f"   fish nearest the mean length {lengths.mean():.1f}: idx {mid.tolist()} lengths {lengths[mid].tolist()}")

    good = np.ones(80, bool); good[BAD] = False
    a78, b78 = ls_fit(lengths[good], weights[good])
    wt = with_typos(weights, BAD)
    a1, b1 = ls_fit(lengths, wt)
    print(f"\n[2 typos: indices {BAD}, lengths {lengths[BAD].tolist()}, weights {weights[BAD].astype(int).tolist()} -> {wt[BAD].astype(int).tolist()}]")
    print(f"   LS on the 78 correct slips: a={a78:.2f} g/cm  b={b78:.1f}")
    print(f"   LS on the 80 with typos:    a={a1:.2f} g/cm  b={b1:.1f}")
    for cm in (45, 50, 55, 62):
        print(f"      prediction at {cm} cm: clean {a0 * cm + b0:6.0f} g  with typos {a1 * cm + b1:6.0f} g")
    err = wt - (a0 * lengths + b0)                        # residuals from the clean 80-fish line
    print(f"   residuals from the clean line: correct slips max {np.abs(err[good]).max():.0f} g, typos {np.abs(err[BAD]).min():.0f}..{np.abs(err[BAD]).max():.0f} g")
    sq_ok, sq_bad = np.sum(err[good] ** 2), np.sum(err[BAD] ** 2)
    print(f"   squared residuals (clean line): 78 correct = {sq_ok:,.0f}, 2 typos = {sq_bad:,.0f}, ratio {sq_bad / sq_ok:,.0f}x")

    print("\n[RANSAC on the 80 slips with 2 typos]")
    ransac_stats("main", lengths, wt, BAD, THRESHOLD, N_TRIALS)
    print("\n[Tweak rows]")
    ransac_stats("threshold 50", lengths, wt, BAD, 50, N_TRIALS)
    ransac_stats("threshold 30000", lengths, wt, BAD, 30000, N_TRIALS)
    ransac_stats("n_trials 3", lengths, wt, BAD, THRESHOLD, 3)
    ransac_stats("n_trials 10", lengths, wt, BAD, THRESHOLD, 10)
    bad_mid = mid[:2].tolist()
    wt_mid = with_typos(weights, bad_mid)
    a_mid, b_mid = ls_fit(lengths, wt_mid)
    print(f"   [typos moved to the middle: idx {bad_mid}, lengths {lengths[bad_mid].tolist()}] LS a={a_mid:.2f} g/cm b={b_mid:.1f}; "
          f"prediction at 45/62 cm: {a_mid * 45 + b_mid:.0f}/{a_mid * 62 + b_mid:.0f} g")
    ransac_stats("typos in the middle", lengths, wt_mid, bad_mid, THRESHOLD, N_TRIALS)
    wt20 = with_typos(weights, BAD20)
    a2, b2 = ls_fit(lengths, wt20)
    print(f"   [20 typos] LS a={a2:.2f} g/cm b={b2:.1f}")
    ransac_stats("20 typos", lengths, wt20, BAD20, THRESHOLD, N_TRIALS)

    w = 78 / 80
    print("\n[how many trials: P(no all-correct pair in N trials) = (1 - w^2)^N, w = 78/80]")
    for n in (1, 3, 10, 200):
        print(f"   N={n:3d}: {(1 - w ** 2) ** n:.4f}")

    print("\n[sklearn RANSACRegressor on the 80 slips with 2 typos]")
    sk = RANSACRegressor(LinearRegression(), residual_threshold=THRESHOLD, random_state=0).fit(lengths.reshape(-1, 1), wt)
    print(f"   a={sk.estimator_.coef_[0]:.2f} b={sk.estimator_.intercept_:.1f} inliers={sk.inlier_mask_.sum()} "
          f"typos excluded={not sk.inlier_mask_[BAD].any()}")

    print("\n[exercise: 5 points A(0,0) B(1,1) C(2,2) D(3,3) E(2,8), threshold 0.5]")
    px = np.array([0.0, 1.0, 2.0, 3.0, 2.0]); pt = np.array([0.0, 1.0, 2.0, 3.0, 8.0])
    a5, b5 = ls_fit(px, pt)
    print(f"   LS on 5 points: a={a5:.4f} b={b5:.4f}")
    for name, (i, j) in {"AB": (0, 1), "AE": (0, 4), "DE": (3, 4)}.items():
        a = (pt[j] - pt[i]) / (px[j] - px[i]); b = pt[i] - a * px[i]
        inl = np.abs(a * px + b - pt) < 0.5
        print(f"   line through {name}: a={a:.1f} b={b:.1f} inliers={inl.sum()} {inl.astype(int).tolist()}")
    results = Counter()
    for s in range(SEEDS):
        np.random.seed(s)
        a, b, inl = ransac_line(px, pt, 0.5)
        results[(round(float(a), 4), round(float(b), 4), int(inl.sum()))] += 1
    np.random.seed()
    print(f"   ransac_line over {SEEDS} seeds: {dict(results)}")
    a, b = 0.0, 0.0
    for i in range(1, 101):
        pred = a * px + b
        a -= 0.1 * 2 * np.mean((pred - pt) * px)
        b -= 0.1 * 2 * np.mean(pred - pt)
    print(f"   gradient descent (lr 0.1, 100 updates) on 5 points: a={a:.4f} b={b:.4f}")


if __name__ == "__main__":
    main()
