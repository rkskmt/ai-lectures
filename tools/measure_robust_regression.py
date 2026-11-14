# Measures every number asserted in the MAE part of robust-regression.qmd
# (外れ値に強い回帰) with the deck's own code, so that doc/measured-log.md can be
# written from this output and never from memory. The RANSAC part of the deck
# is measured by tools/measure_robust_regression_ransac.py.
#
#   data   : the 80 fish defined in the deck (weights read straight out of the
#            .qmd, lengths synthesised with default_rng(42) exactly as the deck
#            does)
#   typos  : the deck multiplies the weight of the two largest fish (indices
#            BAD) by 10: "an extra zero typed on two slips"
#   fit    : MAE gradient descent on standardised length and weight, starting
#            from a = b = 0, exactly as the deck's fit_mae
#   Tweak  : the Tweak rows are not rendered, so they are only measured here
#   optimum: the exact MAE minimiser, found by trying every line through two
#            slips (an MAE minimiser passes through two data points) and
#            cross-checked with a linear program
#
# Usage: python tools/measure_robust_regression.py    (from the repo root)

import re
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "robust-regression.qmd"

BAD = [3, 6]                           # the two heaviest fish, weight x10 (extra zero)


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


def ls_fit(x, t):
    reg = LinearRegression().fit(x.reshape(-1, 1), t)
    return reg.coef_[0], reg.intercept_


def mae_line_by_pairs(x, t):
    """Exact MAE minimiser: try the line through every pair of points with distinct x.

    Also returns every distinct line that attains the minimum (collinear points
    give the same line from several pairs, so lines are compared, not pairs)."""
    best, ties = None, []
    for i, j in combinations(range(len(x)), 2):
        if x[i] == x[j]:
            continue
        a = (t[j] - t[i]) / (x[j] - x[i])
        b = t[i] - a * x[i]
        loss = np.mean(np.abs(a * x + b - t))
        if best is None or loss < best[0] - 1e-9:
            best, ties = (loss, a, b), [(a, b)]
        elif abs(loss - best[0]) <= 1e-9:
            ties.append((a, b))
    lines = {(round(a, 6), round(b, 6)) for a, b in ties}
    return best, lines


def mae_line_by_lp(x, t):
    """Exact MAE minimiser as a linear program: min sum(u + v) s.t. a x + b - t = u - v, u, v >= 0."""
    n = len(x)
    c = np.concatenate([[0.0, 0.0], np.ones(2 * n)])
    A_eq = np.hstack([x.reshape(-1, 1), np.ones((n, 1)), -np.eye(n), np.eye(n)])
    bounds = [(None, None), (None, None)] + [(0, None)] * (2 * n)
    res = linprog(c, A_eq=A_eq, b_eq=t, bounds=bounds, method="highs")
    assert res.success, res.message
    return res.x[0], res.x[1], res.fun / n


def main():
    lengths, weights = load_fish()
    weights_typo = weights.copy()
    weights_typo[BAD] *= 10
    ok = np.ones(80, dtype=bool)
    ok[BAD] = False

    # ---- slide: 伝票に打ち間違いが2枚あった / 二乗で測ると ----
    a_ok, b_ok = ls_fit(lengths, weights)
    a_typo, b_typo = ls_fit(lengths, weights_typo)
    print("[least squares]")
    print(f"   correct 80 slips: a={a_ok:.2f} g/cm   80 slips with 2 typos: a={a_typo:.2f} g/cm")
    error = weights_typo - (a_ok * lengths + b_ok)        # residuals from the correct 80-slip line
    sq_ok, sq_bad = np.sum(error[ok] ** 2), np.sum(error[BAD] ** 2)
    print(f"   squared residuals: 78 correct {sq_ok:,.0f}, 2 typos {sq_bad:,.0f}, ratio {sq_bad / sq_ok:,.0f}x")

    # ---- slide: 対策：ズレを二乗せずに測る（MAE） ----
    abs_ok, abs_bad = np.sum(np.abs(error[ok])), np.sum(np.abs(error[BAD]))
    print("\n[absolute residuals from the correct 80-slip line]")
    print(f"   78 correct {abs_ok:,.0f} g, 2 typos {abs_bad:,.0f} g, ratio {abs_bad / abs_ok:.2f}x")

    # ---- the deck's MAE gradient descent ----
    x = (lengths - lengths.mean()) / lengths.std()
    t = (weights_typo - weights_typo.mean()) / weights_typo.std()

    def to_gram(a, b, cm):
        x_cm = (cm - lengths.mean()) / lengths.std()
        return (a * x_cm + b) * weights_typo.std() + weights_typo.mean()

    def fit_mae(lr, n_updates):
        a, b = 0.0, 0.0
        history = []
        for i in range(n_updates):
            pred = a * x + b
            a -= lr * np.mean(np.sign(pred - t) * x)
            b -= lr * np.mean(np.sign(pred - t))
            history.append(to_gram(a, b, 45))
        return a, b, history

    def slope(a, b):
        return (to_gram(a, b, 62) - to_gram(a, b, 45)) / (62 - 45)

    def mae_gram(a, b):
        return np.mean(np.abs(to_gram(a, b, lengths) - weights_typo))

    print("\n[MAE で fit する: lr 0.1, 100 updates]")
    a, b = 0.0, 0.0
    for i in range(1, 101):
        pred = a * x + b
        a -= 0.1 * np.mean(np.sign(pred - t) * x)
        b -= 0.1 * np.mean(np.sign(pred - t))
        if i in (1, 3, 10, 50, 100):
            print(f"   update {i:3d}: 45 cm {to_gram(a, b, 45):6,.0f} g   62 cm {to_gram(a, b, 62):6,.0f} g")

    print("\n[揺れ続ける: lr 0.1, 300 updates, prediction at 45 cm]")
    a, b, history = fit_mae(0.1, 300)
    last = history[-50:]
    print(f"   last 50 updates: {min(last):,.0f} .. {max(last):,.0f} g (width {max(last) - min(last):,.0f} g)")

    print("\n[揺れる理由]")
    print(f"   std of weights_typo {weights_typo.std():,.0f} g; one step of b at lr 0.1 is at most {0.1 * weights_typo.std():,.0f} g")
    print(f"   residuals of the correct slips from the correct 80-slip line: max {np.abs(error[ok]).max():,.0f} g")

    print("\n[Tweak rows (not rendered): last 50 predictions at 45 cm]")
    for lr, n in ((0.1, 300), (0.01, 300), (0.001, 300), (0.001, 3000)):
        a, b, history = fit_mae(lr, n)
        last = history[-50:]
        falling = all(h1 <= h0 for h0, h1 in zip(last, last[1:]))
        print(f"   lr={lr:<5} n_updates={n:4d}: {min(last):,.0f} .. {max(last):,.0f} g "
              f"(width {max(last) - min(last):,.1f} g, monotonically falling: {falling}); "
              f"slope {slope(a, b):.2f} g/cm, MAE {mae_gram(a, b):.2f} g")

    print("\n[MAE の直線を、MSE の直線と比べる: lr 0.01, 1000 updates]")
    a, b, history = fit_mae(0.01, 1000)
    print(f"   slope {slope(a, b):.1f} g/cm   45 cm {to_gram(a, b, 45):,.0f} g   62 cm {to_gram(a, b, 62):,.0f} g   "
          f"MAE {mae_gram(a, b):.2f} g")

    print("\n[exact MAE minimiser on the 80 slips with 2 typos]")
    (loss, a_ex, b_ex), ties = mae_line_by_pairs(lengths, weights_typo)
    print(f"   pairs: slope {a_ex:.2f} g/cm   45 cm {a_ex * 45 + b_ex:,.0f} g   62 cm {a_ex * 62 + b_ex:,.0f} g   "
          f"MAE {loss:.2f} g   distinct lines attaining the minimum: {len(ties)}")
    a_lp, b_lp, loss_lp = mae_line_by_lp(lengths, weights_typo)
    print(f"   LP   : slope {a_lp:.2f} g/cm   45 cm {a_lp * 45 + b_lp:,.0f} g   62 cm {a_lp * 62 + b_lp:,.0f} g   MAE {loss_lp:.2f} g")
    a_c, b_c = ls_fit(lengths[ok], weights[ok])
    print(f"   (for reference) least squares on the 78 correct slips: slope {a_c:.2f} g/cm")

    print("\n[exercise: 5 points A(0,0) B(1,1) C(2,2) D(3,3) E(2,8)]")
    px = np.array([0.0, 1.0, 2.0, 3.0, 2.0])
    pt = np.array([0.0, 1.0, 2.0, 3.0, 8.0])
    a, b = 0.0, 0.0
    for i in range(100):
        pred = a * px + b
        a -= 0.1 * 2 * np.mean((pred - pt) * px)
        b -= 0.1 * 2 * np.mean(pred - pt)
    print(f"   MSE gradient descent (lr 0.1, 100 updates): a={a:.4f} b={b:.4f}")
    a, b = 0.0, 0.0
    for i in range(10000):
        pred = a * px + b
        a -= 0.001 * np.mean(np.sign(pred - pt) * px)
        b -= 0.001 * np.mean(np.sign(pred - pt))
    print(f"   MAE gradient descent (lr 0.001, 10000 updates): a={a:.4f} b={b:.4f}")
    (loss, a_ex, b_ex), ties = mae_line_by_pairs(px, pt)
    print(f"   exact MAE minimiser: a={a_ex:.4f} b={b_ex:.4f} MAE {loss:.4f}, distinct lines attaining the minimum: {len(ties)}")


if __name__ == "__main__":
    main()
