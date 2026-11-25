"""Measure the polynomial and regularization part of linear-regression.qmd.

From the slide "次数を上げてみる" on, the deck uses one data set of body
length (cm) and weight (g), separate from the fish of the first half.

Part 1 picks that data set. Points are drawn around the line t = x and
shown as length = 20 x cm and weight = 1000 t g; scaling leaves every
standardized feature and target unchanged. The set must serve two figures:
the degree-9 fit that passes every training point and swings between them,
tamed by the L2 penalty, and the x, x^2 fit on the coefficient plane, whose
unpenalized parabola bends visibly and whose coefficients run far out.

Part 2 measures every number and claim the slides show on that data, with
the same code as the deck: exact fits by np.polyfit on standardized length,
and the hand-written gradient descent with the penalty.

Part 3 screens two-feature data sets for the circle and diamond figure.

Usage:
    python tools/measure_linear_regression.py --out results.json
"""
import argparse
import itertools
import json
import warnings

import numpy as np
from sklearn.datasets import load_iris

# Part 1: data for the polynomial part.
POLY_NOISE = 0.35
POLY_N_TRAIN = 10
POLY_TEST_X = np.round(np.linspace(0.9, 3.1, 6), 1)
POLY_SEEDS = 20_000
POLY_CHOSEN_SEED = 16310    # picked by eye among the candidates, see doc/measured-log.md
CM_PER_X, G_PER_X = 20, 1000
# Screening conditions; bends are in units of x (1 = 20 cm, 1000 g).
MIN_BEND_X2 = 0.5           # x, x^2 fit without penalty: largest gap from a line
MIN_RUNAWAY = 3.0           # |w(lambda=0)| / |w(lambda=0.1)| for x, x^2
MAX_AXIS_RATIO = 30.0       # long / short axis of the x, x^2 error ellipse
MAX_TEST_RATIO_X2 = 0.5     # x, x^2 test MSE with the penalty / without
MIN_BLOWUP_DEG9 = 100.0     # degree-9 exact test MSE / degree-1 test MSE
MAX_RIDGE9_VS_DEG1 = 2.0    # degree-9 ridge test MSE / degree-1 test MSE
MAX_WIGGLE_RIDGE9 = 0.5     # degree-9 ridge curve: largest gap from a line

# Part 2: the deck's settings.
DEGREE = 9
LR = 0.01
N_UPDATES = 10_000
GD_LAMBDAS = [0.0, 0.1, 10.0]
PLANE_LAMBDAS = [0.0, 0.01, 0.1, 1.0]
GRID = np.linspace(15, 65, 300)   # the deck's drawing grid in cm

# The 80 fish of dimensionality-pca.qmd: 40 salmon, then 40 sea bass.
FISH_WEIGHTS = np.array([
    2149, 1959, 2194, 2457, 1930, 1930, 2474, 2230, 1859, 2163,
    1861, 1860, 2073, 1426, 1483, 1831, 1696, 2094, 1728, 1576,
    2028, 1903, 2057, 2229, 1884, 1884, 2240, 2081, 1838, 2037,
    1839, 1838, 1978, 1554, 1591, 1820, 1731, 1992, 1752, 1652,
    1677, 1327, 1486, 1440, 1857, 1476, 1749, 2203, 1979, 1468,
    1496, 1737, 1099, 1341, 1748, 1563, 2181, 1414, 1286, 1333,
    1787, 1445, 1505, 1204, 1381, 1513, 1259, 1567, 1370, 1432,
    1370, 1864, 1488, 1278, 1657, 1245, 1533, 1096, 1223, 1531], dtype=float)
FISH_BRIGHTNESS = np.array([
    3.5, 5.8, 4.9, 4.4, 2.6, 2.6, 2.2, 5.5, 4.4, 4.8, 2.1,
    5.9, 5.3, 2.8, 2.7, 2.7, 3.2, 4.1, 3.7, 3.2, 4.4, 2.6,
    3.2, 3.5, 3.8, 5.1, 2.8, 4.1, 4.4, 2.2, 4.4, 2.7, 2.3,
    5.8, 5.9, 5.2, 3.2, 2.4, 4.7, 3.8,
    5.6, 7.5, 5.2, 9.5, 6.3, 8.3, 6.6, 7.6, 7.7, 5.9, 9.8,
    8.9, 9.7, 9.5, 8.0, 9.6, 5.4, 6.0, 5.2, 6.6, 6.9, 6.4,
    9.1, 6.8, 6.4, 7.7, 5.7, 9.0, 5.4, 9.9, 8.9, 6.0, 5.0,
    9.1, 8.5, 8.6, 8.9, 5.4, 6.8, 5.6])
FISH_LENGTHS = np.array([
    58.4, 55.3, 59.2, 61.7, 54.1, 54.7, 61.0, 58.5, 55.3, 57.3,
    56.2, 56.1, 57.4, 51.8, 51.8, 54.2, 54.0, 56.6, 54.9, 52.3,
    56.8, 55.1, 58.5, 58.6, 55.2, 55.2, 59.4, 57.8, 55.5, 57.5,
    57.3, 54.7, 56.0, 51.3, 53.1, 56.1, 53.9, 55.8, 53.4, 53.8,
    54.2, 50.0, 50.7, 51.0, 55.4, 51.5, 55.1, 58.8, 57.2, 51.2,
    51.8, 54.7, 45.0, 49.3, 53.7, 51.6, 58.1, 52.0, 48.1, 50.5,
    52.9, 50.5, 51.7, 48.5, 50.8, 52.5, 48.2, 51.8, 50.8, 50.5,
    48.7, 54.2, 50.5, 49.3, 53.4, 49.1, 51.5, 46.6, 48.7, 51.6])

# Part 3: screening for the circle and diamond figure.
NORM_FRACTIONS = [0.5, 0.6, 0.7, 0.8, 0.9]
MIN_ABS_CORR, MAX_ABS_CORR = 0.2, 0.85
MIN_COEF_RATIO = 0.25
BISECTION_STEPS = 60


def draw_points(seed):
    """Training x uniform on 1 to 3, test x on a fixed grid, t = x plus noise."""
    rng = np.random.default_rng(seed)
    x_train = np.sort(np.round(rng.uniform(1, 3, POLY_N_TRAIN), 1))
    t_train = np.round(x_train + rng.normal(0, POLY_NOISE, POLY_N_TRAIN), 2)
    t_test = np.round(POLY_TEST_X + rng.normal(0, POLY_NOISE, len(POLY_TEST_X)), 2)
    return x_train, t_train, POLY_TEST_X.copy(), t_test


def ridge_fit(x_train, t_train, degree, lam):
    """Closed-form ridge on the standardized powers x^1..x^degree, as in the ridge code."""
    powers = np.arange(1, degree + 1)
    raw = x_train.reshape(-1, 1) ** powers
    mu, sd = raw.mean(axis=0), raw.std(axis=0)
    features = lambda x: (x.reshape(-1, 1) ** powers - mu) / sd
    t_mean, t_std = t_train.mean(), t_train.std()
    P, y = features(x_train), (t_train - t_mean) / t_std
    H, g = P.T @ P / len(y), P.T @ y / len(y)
    if lam > 0:
        w = np.linalg.solve(H + lam * np.eye(degree), g)
    else:
        w = np.linalg.lstsq(P, y, rcond=None)[0]
    return w, (lambda x: features(x) @ w * t_std + t_mean), H


def exact_fit(x_train, t_train, degree):
    """np.polyfit on standardized length, as on the slide "次数を上げてみる"."""
    mean, std = x_train.mean(), x_train.std()
    coef = np.polyfit((x_train - mean) / std, t_train, degree)
    return coef, (lambda x: np.polyval(coef, (x - mean) / std))


def gap_from_line(grid, curve):
    """Largest distance between a curve and its least-squares line."""
    return float(np.abs(curve - np.polyval(np.polyfit(grid, curve, 1), grid)).max())


def screen_poly_data():
    """Part 1: list the seeds whose points meet every condition."""
    grid = np.linspace(POLY_TEST_X.min() - 0.2, POLY_TEST_X.max() + 0.2, 200)
    candidates = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", np.exceptions.RankWarning)
        for seed in range(POLY_SEEDS):
            x_train, t_train, x_test, t_test = draw_points(seed)
            if len(set(x_train)) < POLY_N_TRAIN:
                continue
            mse = lambda f: float(np.mean((f(x_test) - t_test) ** 2))
            w0, f0, H = ridge_fit(x_train, t_train, 2, 0.0)
            w1, f1, _ = ridge_fit(x_train, t_train, 2, 0.1)
            axis_ratio = float(np.sqrt((1 + abs(H[0, 1])) / (1 - abs(H[0, 1]))))
            row = {"seed": seed, "bend_x2": gap_from_line(grid, f0(grid)),
                   "runaway": float(np.linalg.norm(w0) / np.linalg.norm(w1)),
                   "axis_ratio": axis_ratio, "test_x2": mse(f0), "test_x2_ridge": mse(f1)}
            if not (w0[0] * w0[1] < 0 and row["bend_x2"] >= MIN_BEND_X2
                    and row["runaway"] >= MIN_RUNAWAY and axis_ratio <= MAX_AXIS_RATIO
                    and row["test_x2_ridge"] <= MAX_TEST_RATIO_X2 * row["test_x2"]):
                continue
            row["test_deg1"] = mse(exact_fit(x_train, t_train, 1)[1])
            row["test_deg9"] = mse(exact_fit(x_train, t_train, 9)[1])
            _, f9, _ = ridge_fit(x_train, t_train, 9, 0.1)
            row["test_deg9_ridge"] = mse(f9)
            row["wiggle_deg9_ridge"] = gap_from_line(grid, f9(grid))
            if (row["test_deg9"] >= MIN_BLOWUP_DEG9 * row["test_deg1"]
                    and row["test_deg9_ridge"] <= MAX_RIDGE9_VS_DEG1 * row["test_deg1"]
                    and row["wiggle_deg9_ridge"] <= MAX_WIGGLE_RIDGE9):
                candidates.append(row)
    print(f"{len(candidates)} seeds pass; by the bend of the x, x^2 fit:")
    for row in sorted(candidates, key=lambda r: -r["bend_x2"])[:8]:
        print(f"  seed {row['seed']:5d} bend {row['bend_x2']:.2f} runaway {row['runaway']:.1f} "
              f"axis {row['axis_ratio']:4.1f} x2 test {row['test_x2']:.3f} -> "
              f"{row['test_x2_ridge']:.3f} | deg1 {row['test_deg1']:.3f} "
              f"deg9 {row['test_deg9']:.2g} deg9 ridge {row['test_deg9_ridge']:.3f}")
    assert any(row["seed"] == POLY_CHOSEN_SEED for row in candidates)
    return candidates


def poly_data():
    """The chosen points in the deck's units."""
    x_train, t_train, x_test, t_test = draw_points(POLY_CHOSEN_SEED)
    return (np.round(x_train * CM_PER_X), np.round(t_train * G_PER_X),
            np.round(x_test * CM_PER_X), np.round(t_test * G_PER_X))


def fit_gd(x_train, t_train, lam):
    """The deck's ridge code: standardized x^1..x^9, gradient descent with the penalty."""
    powers = np.arange(1, DEGREE + 1)
    raw = x_train.reshape(-1, 1) ** powers
    mu, sd = raw.mean(axis=0), raw.std(axis=0)
    features = lambda x: (x.reshape(-1, 1) ** powers - mu) / sd
    t_mean, t_std = t_train.mean(), t_train.std()
    P, tt = features(x_train), (t_train - t_mean) / t_std
    w, b = np.zeros(DEGREE), 0.0
    for _ in range(N_UPDATES):
        pred = P @ w + b
        grad_w = 2 * P.T @ (pred - tt) / len(tt) + 2 * lam * w
        grad_b = 2 * np.mean(pred - tt)
        w -= LR * grad_w
        b -= LR * grad_b
    return lambda x: (features(x) @ w + b) * t_std + t_mean


def measure_poly():
    """Part 2: the numbers behind the slides from "次数を上げてみる" on."""
    x_train, t_train, x_test, t_test = poly_data()
    print(f"\nchosen seed {POLY_CHOSEN_SEED}")
    print("x_train", x_train.astype(int).tolist(), "\nt_train", t_train.astype(int).tolist())
    print("x_test ", x_test.astype(int).tolist(), "\nt_test ", t_test.astype(int).tolist())
    mse = lambda f, x, t: float(np.mean((f(x) - t) ** 2))
    z_train = (x_train - x_train.mean()) / x_train.std()
    results = {"x_train": x_train.tolist(), "t_train": t_train.tolist(),
               "x_test": x_test.tolist(), "t_test": t_test.tolist(), "exact": {}, "gd": {},
               "plane": {}}

    print("\nexact fits (np.polyfit on standardized length)")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", np.exceptions.RankWarning)
        for degree in range(1, DEGREE + 1):
            coef, f = exact_fit(x_train, t_train, degree)
            curve = f(GRID)
            row = {"train_mse": mse(f, x_train, t_train), "test_mse": mse(f, x_test, t_test),
                   "max_abs_coef": float(np.abs(coef[:-1]).max()),
                   "curve_min": float(curve.min()), "curve_max": float(curve.max()),
                   "test_pred": f(x_test).tolist()}
            results["exact"][degree] = row
            print(f"  degree {degree}: train {row['train_mse']:.4g} test {row['test_mse']:.4g} "
                  f"max|coef| {row['max_abs_coef']:,.0f} curve [{row['curve_min']:,.0f}, "
                  f"{row['curve_max']:,.0f}]")
        f9 = exact_fit(x_train, t_train, DEGREE)[1]
        negative = GRID[f9(GRID) < 0]
        print(f"  degree 9 is negative on {negative.min():.1f}..{negative.max():.1f} cm "
              f"({len(negative)} of {len(GRID)} grid points); test predictions "
              f"{np.round(f9(x_test)).astype(int).tolist()}")

    print("\ngradient descent (lr 0.01, 10,000 updates)")
    for lam in GD_LAMBDAS:
        f = fit_gd(x_train, t_train, lam)
        coef_own = np.polyfit(z_train, f(x_train), DEGREE)
        curve = f(GRID)
        inside = curve[(GRID >= x_train.min()) & (GRID <= x_train.max())]
        row = {"train_mse": mse(f, x_train, t_train), "test_mse": mse(f, x_test, t_test),
               "max_abs_coef": float(np.abs(coef_own[:-1]).max()),
               "curve_min": float(curve.min()), "curve_max": float(curve.max()),
               "inside_min": float(inside.min()), "inside_max": float(inside.max()),
               "wiggle": gap_from_line(GRID, curve)}
        results["gd"][lam] = row
        print(f"  lam {lam:<4}: train {row['train_mse']:,.0f} test {row['test_mse']:,.0f} "
              f"max|coef| {row['max_abs_coef']:,.0f} curve [{row['curve_min']:,.0f}, "
              f"{row['curve_max']:,.0f}], within the training lengths "
              f"[{row['inside_min']:,.0f}, {row['inside_max']:,.0f}]")

    print("\nx and x^2 only (the coefficient plane)")
    _, _, H = ridge_fit(x_train, t_train, 2, 0.0)
    results["plane"]["corr"] = float(H[0, 1])
    results["plane"]["axis_ratio"] = float(np.sqrt((1 + H[0, 1]) / (1 - H[0, 1])))
    print(f"  corr {H[0, 1]:.4f}, ellipse axis ratio {results['plane']['axis_ratio']:.1f}")
    for lam in PLANE_LAMBDAS:
        w, f, _ = ridge_fit(x_train, t_train, 2, lam)
        row = {"w": w.tolist(), "l2_norm": float(np.linalg.norm(w)),
               "train_mse": mse(f, x_train, t_train), "test_mse": mse(f, x_test, t_test),
               "gap_from_line": gap_from_line(GRID, f(GRID))}
        results["plane"][lam] = row
        print(f"  lam {lam:<4}: w ({w[0]:+.4f}, {w[1]:+.4f}) |w| {row['l2_norm']:.4f} "
              f"train {row['train_mse']:,.0f} test {row['test_mse']:,.0f} "
              f"gap from a line {row['gap_from_line']:,.0f}")
    return results


def standardize(a):
    """Scale to mean 0 and standard deviation 1 along the first axis."""
    return (a - a.mean(axis=0)) / a.std(axis=0)


def contour_cases():
    """List the two-feature regressions to screen."""
    iris = load_iris()
    names = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
    cases = [("fish80: weight ~ length + brightness",
              np.column_stack([FISH_LENGTHS, FISH_BRIGHTNESS]), FISH_WEIGHTS)]
    for target in range(4):
        rest = [c for c in range(4) if c != target]
        for f0, f1 in itertools.combinations(rest, 2):
            cases.append((f"iris: {names[target]} ~ {names[f0]} + {names[f1]}",
                          iris.data[:, [f0, f1]], iris.data[:, target]))
    return cases


def ridge_at_norm(H, g, r):
    """Find the ridge solution whose L2 norm equals r."""
    low, high = 0.0, 1e6
    for _ in range(BISECTION_STEPS):
        lam = (low + high) / 2
        if np.linalg.norm(np.linalg.solve(H + lam * np.eye(2), g)) > r:
            low = lam
        else:
            high = lam
    return np.linalg.solve(H + high * np.eye(2), g), high


def lasso_2d(H, g, lam):
    """Solve the two-coefficient lasso by coordinate descent on H and g."""
    w = [0.0, 0.0]
    for _ in range(100_000):
        previous = list(w)
        for j, k in ((0, 1), (1, 0)):
            rho = g[j] - H[j, k] * w[k]
            w[j] = float(np.sign(rho)) * max(abs(rho) - lam / 2, 0.0)
        if max(abs(w[0] - previous[0]), abs(w[1] - previous[1])) < 1e-13:
            return np.array(w)
    raise RuntimeError(f"lasso_2d did not converge for lam={lam}")


def lasso_at_norm(H, g, r):
    """Find the lasso solution whose L1 norm equals r."""
    low, high = 0.0, 2 * float(np.abs(g).max())
    for _ in range(BISECTION_STEPS):
        lam = (low + high) / 2
        if np.abs(lasso_2d(H, g, lam)).sum() > r:
            low = lam
        else:
            high = lam
    return lasso_2d(H, g, high), high


def measure_contour_cases():
    """Part 3: find datasets that show the circle and diamond contact clearly."""
    results = []
    print("\ncontour candidates (rows meet every screening condition)")
    print(f"{'case':52} {'corr':>6} {'w_ols':>16} {'frac':>4} {'w_ridge':>16} "
          f"{'lam_r':>7} {'w_lasso':>16} {'lam_l':>7}")
    for name, features, target in contour_cases():
        X, y = standardize(features), standardize(target)
        H, g = X.T @ X / len(y), X.T @ y / len(y)
        w_ols = np.linalg.solve(H, g)
        ols_ratio = float(np.abs(w_ols).min() / np.abs(w_ols).max())
        row = {"case": name, "corr": float(H[0, 1]), "w_ols": w_ols.tolist(),
               "ols_ratio": ols_ratio, "fractions": []}
        for frac in NORM_FRACTIONS:
            r = frac * float(np.linalg.norm(w_ols))
            w_ridge, lam_ridge = ridge_at_norm(H, g, r)
            w_lasso, lam_lasso = lasso_at_norm(H, g, r)
            ridge_ratio = float(np.abs(w_ridge).min() / np.abs(w_ridge).max())
            on_corner = int(np.count_nonzero(w_lasso)) == 1
            passes = (MIN_ABS_CORR <= abs(row["corr"]) <= MAX_ABS_CORR
                      and ols_ratio >= MIN_COEF_RATIO
                      and on_corner and ridge_ratio >= MIN_COEF_RATIO)
            row["fractions"].append({
                "frac": frac, "r": r, "w_ridge": w_ridge.tolist(), "lam_ridge": lam_ridge,
                "w_lasso": w_lasso.tolist(), "lam_lasso": lam_lasso,
                "ridge_ratio": ridge_ratio, "lasso_on_corner": on_corner, "passes": passes,
            })
            if passes:
                print(f"{name:52} {row['corr']:6.3f} "
                      f"({w_ols[0]:6.3f},{w_ols[1]:6.3f}) {frac:4} "
                      f"({w_ridge[0]:6.3f},{w_ridge[1]:6.3f}) {lam_ridge:7.4f} "
                      f"({w_lasso[0]:6.3f},{w_lasso[1]:6.3f}) {lam_lasso:7.4f}")
        results.append(row)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="path of the JSON result file")
    args = parser.parse_args()

    results = {"poly_candidates": screen_poly_data(), "poly": measure_poly(),
               "contour_cases": measure_contour_cases()}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
