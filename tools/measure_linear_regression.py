"""Measure ridge and lasso for linear-regression.qmd.

Part 1 uses the deck's degree-9 features. It solves both penalties to
convergence with scikit-learn and checks two things the deck shows students:
the hand-written coordinate descent, and the scikit-learn settings.

Part 2 screens two-feature datasets for the contour figure, which needs a
tilted error ellipse, a lasso solution on a corner of the L1 region, and a
ridge solution that keeps both coefficients at the same norm.

Part 3 picks a small synthetic data set for the ridge figure on the
coefficient plane: with only x and x^2 as features, the unpenalized fit must
bend visibly and its coefficients must run far from the origin, while the
error ellipse stays wide enough to read.

Usage:
    python tools/measure_linear_regression.py --out results.json
"""
import argparse
import itertools
import json
import warnings

import numpy as np
from sklearn.datasets import load_iris
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import Lasso, Ridge

LENGTHS = np.array([55.2, 56.0, 51.8, 58.1, 56.8, 51.5, 56.6, 51.6, 61.0, 52.0,
                    58.5, 50.5, 55.5, 48.7, 46.6])
WEIGHTS = np.array([1884, 1978, 1483, 2181, 2028, 1476, 2094, 1563, 2474, 1414,
                    2230, 1445, 1838, 1370, 1096], dtype=float)
N_TRAIN = 10
DEGREE = 9
LR = 0.01
N_UPDATES = 10_000
LAMBDAS = [0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3]
STUDENT_MAX_ITER = 100_000
CD_SWEEPS = 1000
# Values already logged in doc/measured-log.md for the deck's ridge run.
LOGGED_RIDGE_TRAIN_MSE = 3585
LOGGED_RIDGE_TEST_MSE = 3427

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

# Screening for the contour figure.
NORM_FRACTIONS = [0.5, 0.6, 0.7, 0.8, 0.9]
MIN_ABS_CORR, MAX_ABS_CORR = 0.2, 0.85
MIN_COEF_RATIO = 0.25
BISECTION_STEPS = 60

# Synthetic data for the ridge figure: noisy points around t = x.
SYN_NOISE = 0.25
SYN_N_TEST = 8
SYN_N_TRAIN = [5, 6]
SYN_SEEDS = 4000
SYN_LAMBDA = 0.1
SYN_MIN_RUNAWAY = 3.0       # |w_ols| / |w_ridge|
SYN_MAX_AXIS_RATIO = 15.0   # long / short axis of the error ellipse
SYN_MIN_BEND = 0.5          # largest gap between the fitted parabola and a line
SYN_MAX_TEST_RATIO = 0.4    # test MSE with the penalty / without
SYN_CHOSEN = (6, 429)
SYN_REPORT_LAMBDAS = [0.0, 0.01, 0.1, 1.0]


def prepare():
    """Build the standardized features and target exactly as the deck does."""
    powers = np.arange(1, DEGREE + 1)
    x_train, x_test = LENGTHS[:N_TRAIN], LENGTHS[N_TRAIN:]
    t_train, t_test = WEIGHTS[:N_TRAIN], WEIGHTS[N_TRAIN:]
    P_train = x_train.reshape(-1, 1) ** powers
    P_test = x_test.reshape(-1, 1) ** powers
    mu, sd = P_train.mean(axis=0), P_train.std(axis=0)
    grid = np.linspace(LENGTHS.min() - 0.5, LENGTHS.max() + 0.5, 300)
    return {
        "P_train": (P_train - mu) / sd,
        "P_test": (P_test - mu) / sd,
        "P_grid": (grid.reshape(-1, 1) ** powers - mu) / sd,
        "t_train": t_train,
        "t_test": t_test,
        "t_mean": t_train.mean(),
        "t_std": t_train.std(),
    }


def fit_ridge_gd(P, y, lam):
    """Run the deck's gradient descent for the L2 penalty."""
    w, b = np.zeros(P.shape[1]), 0.0
    for _ in range(N_UPDATES):
        residual = P @ w + b - y
        w = w - LR * (2 * P.T @ residual / len(y) + 2 * lam * w)
        b = b - LR * 2 * residual.mean()
    return w, b


def coordinate_descent(P, y, penalty, lam):
    """Run the coordinate descent shown in the deck on standardized data."""
    coef = np.zeros(P.shape[1])
    for _ in range(CD_SWEEPS):
        for j in range(P.shape[1]):
            coef[j] = 0.0
            rho = np.mean((y - P @ coef) * P[:, j])
            if penalty == "ridge":
                coef[j] = rho / (1 + lam)
            else:
                coef[j] = np.sign(rho) * max(abs(rho) - lam / 2, 0)
    return coef


def support(w):
    """Return the degrees whose coefficient is exactly nonzero."""
    return [int(d) + 1 for d in np.flatnonzero(w)]


def summarize(data, w, b):
    """Report errors in grams and the shape of the fitted curve."""
    to_grams = lambda P: (P @ w + b) * data["t_std"] + data["t_mean"]
    curve = to_grams(data["P_grid"])
    return {
        "w": np.asarray(w).tolist(),
        "b": float(b),
        "n_nonzero": int(np.count_nonzero(w)),
        "support": support(w),
        "min_abs_w": float(np.abs(w).min()),
        "max_abs_w": float(np.abs(w).max()),
        "train_mse": float(np.mean((to_grams(data["P_train"]) - data["t_train"]) ** 2)),
        "test_mse": float(np.mean((to_grams(data["P_test"]) - data["t_test"]) ** 2)),
        "curve_min": float(curve.min()),
        "curve_max": float(curve.max()),
    }


def student_lasso(P, y, lam):
    """Fit with the scikit-learn settings shown on the slide, recording warnings."""
    model = Lasso(alpha=lam / 2, max_iter=STUDENT_MAX_ITER)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(P, y)
    n_warned = sum(issubclass(c.category, ConvergenceWarning) for c in caught)
    return model, n_warned


def measure_degree9():
    """Part 1: compare the penalties on the deck's degree-9 features."""
    data = prepare()
    P, y = data["P_train"], (data["t_train"] - data["t_mean"]) / data["t_std"]

    baseline = summarize(data, *fit_ridge_gd(P, y, 0.1))
    assert round(baseline["train_mse"]) == LOGGED_RIDGE_TRAIN_MSE, baseline["train_mse"]
    assert round(baseline["test_mse"]) == LOGGED_RIDGE_TEST_MSE, baseline["test_mse"]

    results = {"ridge_gd_lam_0.1": baseline, "ridge": {}, "lasso": {}}
    print(f"{'penalty':7} {'lam':>7} {'nonzero':>7} {'train':>9} {'test':>11} "
          f"{'cd_gap':>9}  support")
    for lam in LAMBDAS:
        model = Ridge(alpha=len(y) * lam).fit(P, y)
        ridge = summarize(data, model.coef_, model.intercept_)
        ridge["cd_max_coef_gap"] = float(
            np.abs(coordinate_descent(P, y, "ridge", lam) - model.coef_).max())
        results["ridge"][str(lam)] = ridge
        print(f"{'ridge':7} {lam:7} {ridge['n_nonzero']:7d} {ridge['train_mse']:9.0f} "
              f"{ridge['test_mse']:11.0f} {ridge['cd_max_coef_gap']:9.1e}  {ridge['support']}")

        exact = Lasso(alpha=lam / 2, max_iter=10_000_000, tol=1e-12).fit(P, y)
        lasso = summarize(data, exact.coef_, exact.intercept_)
        cd_coef = coordinate_descent(P, y, "lasso", lam)
        lasso["cd_max_coef_gap"] = float(np.abs(cd_coef - exact.coef_).max())
        lasso["cd_support"] = support(cd_coef)
        shown, n_warned = student_lasso(P, y, lam)
        lasso["student_n_iter"] = int(shown.n_iter_)
        lasso["student_n_warnings"] = n_warned
        lasso["student_support"] = support(shown.coef_)
        lasso["student_max_coef_gap"] = float(np.abs(shown.coef_ - exact.coef_).max())
        results["lasso"][str(lam)] = lasso
        print(f"{'lasso':7} {lam:7} {lasso['n_nonzero']:7d} {lasso['train_mse']:9.0f} "
              f"{lasso['test_mse']:11.0f} {lasso['cd_max_coef_gap']:9.1e}  {lasso['support']} "
              f"cd={lasso['cd_support']} student={lasso['student_support']}")
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
    """Part 2: find datasets that show the circle and diamond contact clearly."""
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


def synthetic_data(n_train, seed):
    """Draw points around the line t = x: random training x, a fixed grid of test x."""
    rng = np.random.default_rng(seed)
    x_train = np.sort(np.round(rng.uniform(1, 3, n_train), 1))
    t_train = np.round(x_train + rng.normal(0, SYN_NOISE, n_train), 2)
    x_test = np.round(np.linspace(0.6, 3.4, SYN_N_TEST), 1)
    t_test = np.round(x_test + rng.normal(0, SYN_NOISE, SYN_N_TEST), 2)
    return x_train, t_train, x_test, t_test


def fit_x_x2(x_train, t_train, lam):
    """Ridge on the standardized x and x^2 columns, as in the deck's ridge code."""
    powers = x_train.reshape(-1, 1) ** np.arange(1, 3)
    mu, sd = powers.mean(axis=0), powers.std(axis=0)
    features = lambda x: (x.reshape(-1, 1) ** np.arange(1, 3) - mu) / sd
    t_mean, t_std = t_train.mean(), t_train.std()
    P, y = features(x_train), (t_train - t_mean) / t_std
    H, g = P.T @ P / len(y), P.T @ y / len(y)
    w = np.linalg.solve(H + lam * np.eye(2), g)
    return w, (lambda x: (features(x) @ w) * t_std + t_mean), H


def screen_synthetic():
    """Part 3: find a small data set whose x, x^2 fit bends visibly and runs away."""
    print("\nsynthetic candidates (n, seed, corr, axis ratio, |w_ols|/|w_ridge|, bend, test MSE)")
    grid = np.linspace(0.5, 3.5, 200)
    candidates = []
    for n_train in SYN_N_TRAIN:
        for seed in range(SYN_SEEDS):
            x_train, t_train, x_test, t_test = synthetic_data(n_train, seed)
            if len(set(x_train)) < n_train:
                continue
            w_ols, f_ols, H = fit_x_x2(x_train, t_train, 0.0)
            w_ridge, f_ridge, _ = fit_x_x2(x_train, t_train, SYN_LAMBDA)
            axis_ratio = float(np.sqrt((1 + abs(H[0, 1])) / (1 - abs(H[0, 1]))))
            runaway = float(np.linalg.norm(w_ols) / np.linalg.norm(w_ridge))
            curve = f_ols(grid)
            bend = float(np.abs(curve - np.polyval(np.polyfit(grid, curve, 1), grid)).max())
            test_ols = float(np.mean((f_ols(x_test) - t_test) ** 2))
            test_ridge = float(np.mean((f_ridge(x_test) - t_test) ** 2))
            if (w_ols[0] * w_ols[1] < 0 and runaway >= SYN_MIN_RUNAWAY
                    and axis_ratio <= SYN_MAX_AXIS_RATIO and bend >= SYN_MIN_BEND
                    and test_ridge <= SYN_MAX_TEST_RATIO * test_ols):
                candidates.append({"n_train": n_train, "seed": seed, "corr": float(H[0, 1]),
                                   "axis_ratio": axis_ratio, "runaway": runaway, "bend": bend,
                                   "test_ols": test_ols, "test_ridge": test_ridge})
    for c in sorted(candidates, key=lambda c: -c["bend"])[:8]:
        print(f"n={c['n_train']} seed={c['seed']:4d} corr={c['corr']:.3f} axis={c['axis_ratio']:4.1f} "
              f"runaway={c['runaway']:.1f} bend={c['bend']:.2f} "
              f"test {c['test_ols']:.3f} -> {c['test_ridge']:.3f}")
    print(f"{len(candidates)} candidates pass")
    return candidates


def measure_synthetic():
    """Part 3: report the chosen data set and its fits for the deck."""
    x_train, t_train, x_test, t_test = synthetic_data(*SYN_CHOSEN)
    _, _, H = fit_x_x2(x_train, t_train, 0.0)
    results = {"n_train_seed": list(SYN_CHOSEN), "x_train": x_train.tolist(),
               "t_train": t_train.tolist(), "x_test": x_test.tolist(), "t_test": t_test.tolist(),
               "corr": float(H[0, 1]),
               "axis_ratio": float(np.sqrt((1 + H[0, 1]) / (1 - H[0, 1]))), "fits": {}}
    print(f"\nchosen n={SYN_CHOSEN[0]} seed={SYN_CHOSEN[1]}")
    print("x_train", x_train.tolist(), "\nt_train", t_train.tolist())
    print("x_test ", x_test.tolist(), "\nt_test ", t_test.tolist())
    print(f"corr {results['corr']:.4f}, ellipse axis ratio {results['axis_ratio']:.1f}")
    for lam in SYN_REPORT_LAMBDAS:
        w, f, _ = fit_x_x2(x_train, t_train, lam)
        fit = {"w": w.tolist(), "l2_norm": float(np.linalg.norm(w)),
               "train_mse": float(np.mean((f(x_train) - t_train) ** 2)),
               "test_mse": float(np.mean((f(x_test) - t_test) ** 2))}
        results["fits"][str(lam)] = fit
        print(f"lam={lam:<5} w=({w[0]:+.4f}, {w[1]:+.4f}) |w|={fit['l2_norm']:.4f} "
              f"train {fit['train_mse']:.4f} test {fit['test_mse']:.4f}")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="path of the JSON result file")
    args = parser.parse_args()

    results = measure_degree9()
    results["contour_cases"] = measure_contour_cases()
    results["synthetic_candidates"] = screen_synthetic()
    results["synthetic"] = measure_synthetic()
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
