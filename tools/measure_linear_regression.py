"""Measure ridge and lasso on the degree-9 features of linear-regression.qmd.

Both penalties are solved to convergence with scikit-learn, because plain
gradient descent cannot reach the lasso solution: the L1 penalty is not
differentiable at zero. The script also checks the Lasso settings the deck
shows to students against a high-precision solution.

Usage:
    python tools/measure_linear_regression.py --out results.json
"""
import argparse
import json
import warnings

import numpy as np
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
# Values already logged in doc/measured-log.md for the deck's ridge run.
LOGGED_RIDGE_TRAIN_MSE = 3585
LOGGED_RIDGE_TEST_MSE = 3427


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
    """Fit with the settings shown on the slide and record any warning."""
    model = Lasso(alpha=lam / 2, max_iter=STUDENT_MAX_ITER)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(P, y)
    n_warned = sum(issubclass(c.category, ConvergenceWarning) for c in caught)
    return model, n_warned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="path of the JSON result file")
    args = parser.parse_args()

    data = prepare()
    P, y = data["P_train"], (data["t_train"] - data["t_mean"]) / data["t_std"]

    baseline = summarize(data, *fit_ridge_gd(P, y, 0.1))
    assert round(baseline["train_mse"]) == LOGGED_RIDGE_TRAIN_MSE, baseline["train_mse"]
    assert round(baseline["test_mse"]) == LOGGED_RIDGE_TEST_MSE, baseline["test_mse"]

    results = {"ridge_gd_lam_0.1": baseline, "ridge": {}, "lasso": {}}
    print(f"{'penalty':7} {'lam':>7} {'nonzero':>7} {'train':>9} {'test':>11} "
          f"{'curve_min':>10} {'curve_max':>10}  support")
    for lam in LAMBDAS:
        model = Ridge(alpha=len(y) * lam).fit(P, y)
        ridge = summarize(data, model.coef_, model.intercept_)
        results["ridge"][str(lam)] = ridge
        print(f"{'ridge':7} {lam:7} {ridge['n_nonzero']:7d} {ridge['train_mse']:9.0f} "
              f"{ridge['test_mse']:11.0f} {ridge['curve_min']:10.0f} "
              f"{ridge['curve_max']:10.0f}  {ridge['support']}")

        exact = Lasso(alpha=lam / 2, max_iter=10_000_000, tol=1e-12).fit(P, y)
        lasso = summarize(data, exact.coef_, exact.intercept_)
        shown, n_warned = student_lasso(P, y, lam)
        lasso["student_n_iter"] = int(shown.n_iter_)
        lasso["student_n_warnings"] = n_warned
        lasso["student_support"] = support(shown.coef_)
        lasso["student_support_matches"] = lasso["student_support"] == lasso["support"]
        lasso["student_max_coef_gap"] = float(np.abs(shown.coef_ - exact.coef_).max())
        results["lasso"][str(lam)] = lasso
        print(f"{'lasso':7} {lam:7} {lasso['n_nonzero']:7d} {lasso['train_mse']:9.0f} "
              f"{lasso['test_mse']:11.0f} {lasso['curve_min']:10.0f} "
              f"{lasso['curve_max']:10.0f}  {lasso['support']} "
              f"student={lasso['student_support']} iter={lasso['student_n_iter']} "
              f"warn={n_warned} gap={lasso['student_max_coef_gap']:.4f}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
