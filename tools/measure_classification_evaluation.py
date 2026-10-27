# Measures every number asserted in classification-evaluation.qmd (過学習と汎化)
# with the deck's own recipe, so that doc/measured-log.md can be written from
# this output and never from memory.
#
#   data   : the 120 fish defined in the deck (60 Salmon + 60 Sea bass), read
#            straight out of the .qmd so the two can never drift apart
#   metrics: Precision and Recall with Salmon (label 1) as the positive class;
#            Accuracy is deliberately not used in this deck
#   trees  : DecisionTreeClassifier(random_state=42) throughout
#   split  : train_test_split(test_size=0.2, random_state=42) -> 96 / 24 fish
#
# Usage: python tools/measure_classification_evaluation.py    (from the repo root)

import re
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix, precision_score, recall_score
from sklearn.model_selection import (KFold, StratifiedKFold, cross_val_score,
                                     train_test_split)
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "classification-evaluation.qmd"
RS = 42


def load_fish():
    src = DECK.read_text(encoding="utf-8")

    def arr(name):
        m = re.search(name + r"\s*=\s*np\.array\(\[(.*?)\]", src, re.S)
        return np.array([float(v) for v in re.findall(r"[-\d.]+", m.group(1))])

    sw, sb = arr("salmon_weights"), arr("salmon_brightness")
    bw, bb = arr("seabass_weights"), arr("seabass_brightness")
    assert len(sw) == len(sb) == len(bw) == len(bb) == 60
    X = np.array([[sb[i], sw[i]] for i in range(60)] + [[bb[i], bw[i]] for i in range(60)])
    y = np.array([1] * 60 + [0] * 60)
    return X, y


def tree(depth):
    return DecisionTreeClassifier(max_depth=depth, random_state=RS)


def pr(y_true, y_pred):
    return precision_score(y_true, y_pred), recall_score(y_true, y_pred)


def fmt(p, r):
    return f"P {p:.3f} / R {r:.3f}"


def main():
    X, y = load_fish()
    print(f"fish: {len(X)} (Salmon {np.sum(y == 1)}, Sea bass {np.sum(y == 0)})")

    print("\n[A] unlimited tree, fit and score on all 120")
    m = tree(None).fit(X, y)
    print("  ", fmt(*pr(y, m.predict(X))))

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=RS)
    print(f"\n[B] hold-out rs{RS}: train {len(X_tr)} / test {len(X_te)}"
          f" (test Salmon {np.sum(y_te == 1)}, Sea bass {np.sum(y_te == 0)})")
    deep = tree(None).fit(X_tr, y_tr)
    print("   train:", fmt(*pr(y_tr, deep.predict(X_tr))))
    print("   test :", fmt(*pr(y_te, deep.predict(X_te))))
    cm = confusion_matrix(y_te, deep.predict(X_te), labels=[1, 0])
    TP, FN, FP, TN = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]
    print(f"   test confusion (Salmon positive): TP {TP}  FN {FN}  FP {FP}  TN {TN}")
    print(f"   check: P = {TP}/{TP + FP} = {TP / (TP + FP):.3f}, R = {TP}/{TP + FN} = {TP / (TP + FN):.3f}")
    print(f"   one missed Salmon moves Recall by 1/{TP + FN} = {1 / (TP + FN):.3f}")
    print(f"   leaves of the unlimited tree: {deep.get_n_leaves()}")

    print(f"\n[C] depth sweep on the rs{RS} split (train | test)")
    for d in list(range(1, 13)) + [None]:
        m = tree(d).fit(X_tr, y_tr)
        print(f"   depth {str(d):>4}: train {fmt(*pr(y_tr, m.predict(X_tr)))} | test {fmt(*pr(y_te, m.predict(X_te)))}")

    print("\n[D] hold-out luck: unlimited tree, test_size=0.2, seeds 0..4")
    for seed in range(5):
        a, b, c, e = train_test_split(X, y, test_size=0.2, random_state=seed)
        m = tree(None).fit(a, c)
        print(f"   seed {seed}: test {fmt(*pr(e, m.predict(b)))}")

    print("\n[E] cross_val_score on all 120, unlimited tree")
    for cv in (5, 10):
        for sc in ("recall", "precision"):
            s = cross_val_score(tree(None), X, y, cv=cv, scoring=sc)
            print(f"   cv={cv:2d} {sc:9s}: folds {np.round(s, 3)}  mean {s.mean():.3f} +- {s.std():.3f}")

    print("\n[F] Tweak checkpoints (unlimited tree)")
    a, b, c, e = train_test_split(X, y, test_size=0.2, random_state=4)
    print("   random_state=4  :", fmt(*pr(e, tree(None).fit(a, c).predict(b))))
    a, b, c, e = train_test_split(X, y, test_size=0.5, random_state=RS)
    print(f"   test_size=0.5   : train {len(a)} / test {len(b)} ->", fmt(*pr(e, tree(None).fit(a, c).predict(b))))

    print("\n[G] fold composition on the sorted 120 (test fold: Salmon / Sea bass)")
    for name, splitter in (("KFold", KFold(n_splits=5)), ("StratifiedKFold", StratifiedKFold(n_splits=5))):
        comp = [(int(np.sum(y[te] == 1)), int(np.sum(y[te] == 0))) for _, te in splitter.split(X, y)]
        print(f"   {name:16s}: {comp}")

    print(f"\n[H] choose depth by 5-fold CV inside the training 96 (rs{RS} split), then test once")
    depths = list(range(1, 11))
    cv_r, cv_p = [], []
    for d in depths:
        r = cross_val_score(tree(d), X_tr, y_tr, cv=5, scoring="recall").mean()
        p = cross_val_score(tree(d), X_tr, y_tr, cv=5, scoring="precision").mean()
        cv_r.append(r)
        cv_p.append(p)
        print(f"   depth {d:2d}: CV mean Recall {r:.3f}  Precision {p:.3f}")
    best_r = depths[int(np.argmax(cv_r))]
    best_p = depths[int(np.argmax(cv_p))]
    print(f"   best depth by CV Recall: {best_r}   by CV Precision: {best_p}")
    for d in sorted({best_r, best_p}):
        m = tree(d).fit(X_tr, y_tr)
        print(f"   depth {d} fit on all 96 -> test {fmt(*pr(y_te, m.predict(X_te)))}")
    print(f"   unlimited tree         -> test {fmt(*pr(y_te, deep.predict(X_te)))}")

    print("\n[I] same selection with cv=10 (Tweak variant)")
    cv_r10 = [cross_val_score(tree(d), X_tr, y_tr, cv=10, scoring="recall").mean() for d in depths]
    print(f"   best depth by CV Recall (cv=10): {depths[int(np.argmax(cv_r10))]}  means {np.round(cv_r10, 3)}")

    manual_kfold_claims(X, y)


def kfold_scores(depth, X, y, k, seed):
    """The deck's hand-written k-fold: rows already in random order, group = position % k.

    Returns per-group (precision, recall) arrays and the number of groups whose
    Precision or Recall was undefined (no predicted / no true Salmon)."""
    group = np.arange(len(y)) % k
    ps, rs, undefined = [], [], 0
    for i in range(k):
        m = DecisionTreeClassifier(max_depth=depth, random_state=seed)
        m.fit(X[group != i], y[group != i])
        pred, true = m.predict(X[group == i]), y[group == i]
        if np.sum(pred == 1) == 0 or np.sum(true == 1) == 0:
            undefined += 1
            continue
        p, r = pr(true, pred)
        ps.append(p)
        rs.append(r)
    return np.array(ps), np.array(rs), undefined


def spread(a):
    q = np.percentile(a, [0, 5, 50, 95, 100])
    return f"min {q[0]:.3f}  5% {q[1]:.3f}  med {q[2]:.3f}  95% {q[3]:.3f}  max {q[4]:.3f}"


def manual_kfold_claims(X, y, trials=1000):
    """Claims for the hand-written k-fold slides. Shuffles and tree seeds vary per
    trial (the deck uses neither a shuffle seed nor a tree seed)."""
    print(f"\n[J] hand-written k-fold on all 120, unlimited tree, {trials} random shuffles")
    mean5_p, mean5_r, hold_p, hold_r = [], [], [], []
    wider_std, wider_range, undef = 0, 0, {5: 0, 10: 0}
    salmon10 = []
    for t in range(trials):
        rng = np.random.default_rng(t)
        idx = rng.permutation(len(y))
        Xs, ys = X[idx], y[idx]
        p5, r5, u5 = kfold_scores(None, Xs, ys, 5, t)
        p10, r10, u10 = kfold_scores(None, Xs, ys, 10, t)
        undef[5] += u5
        undef[10] += u10
        mean5_p.append(p5.mean())
        mean5_r.append(r5.mean())
        wider_std += (r10.std() > r5.std()) and (p10.std() > p5.std())
        wider_range += (np.ptp(r10) > np.ptp(r5)) and (np.ptp(p10) > np.ptp(p5))
        group10 = np.arange(len(y)) % 10
        salmon10 += [int(np.sum(ys[group10 == i] == 1)) for i in range(10)]
        # single 96/24 hold-out on the same shuffle, for the "less luck-dependent" claim
        m = DecisionTreeClassifier(random_state=t).fit(Xs[:96], ys[:96])
        hp, hr = pr(ys[96:], m.predict(Xs[96:]))
        hold_p.append(hp)
        hold_r.append(hr)
    print(f"   5-fold mean P : {spread(mean5_p)}  sd {np.std(mean5_p):.3f}")
    print(f"   5-fold mean R : {spread(mean5_r)}  sd {np.std(mean5_r):.3f}")
    print(f"   hold-out P    : {spread(hold_p)}  sd {np.std(hold_p):.3f}")
    print(f"   hold-out R    : {spread(hold_r)}  sd {np.std(hold_r):.3f}")
    print(f"   k=10 per-group sd > k=5 (both P and R): {wider_std / trials:.1%}")
    print(f"   k=10 per-group max-min > k=5 (both P and R): {wider_range / trials:.1%}")
    print(f"   Salmon per k=10 group: {spread(salmon10)}")
    print(f"   undefined groups: k=5 {undef[5]} of {5 * trials}, k=10 {undef[10]} of {10 * trials}")

    print(f"\n[K] depth chosen by hand-written 5-fold inside the training 96, {trials} random splits")
    differ, best_p_count, undef96 = 0, {}, 0
    for t in range(trials):
        rng = np.random.default_rng(t)
        idx = rng.permutation(len(y))
        Xtr, ytr = X[idx][:96], y[idx][:96]
        cv_p, cv_r = [], []
        for d in range(1, 11):
            p, r, u = kfold_scores(d, Xtr, ytr, 5, t)
            undef96 += u
            cv_p.append(p.mean())
            cv_r.append(r.mean())
        bp, br = int(np.argmax(cv_p)) + 1, int(np.argmax(cv_r)) + 1
        differ += bp != br
        best_p_count[bp] = best_p_count.get(bp, 0) + 1
    print(f"   Precision-chosen depth != Recall-chosen depth: {differ / trials:.1%}")
    print(f"   Precision-chosen depth counts: {dict(sorted(best_p_count.items()))}")
    print(f"   undefined groups: {undef96} of {5 * 10 * trials}")

    print(f"\n[L] cross-validation inside the training 96 (validation data), unlimited tree, {trials} random splits")
    mean5_p, mean5_r, hold_p, hold_r, sal_val, sal10 = [], [], [], [], [], []
    wider_std, wider_range, undef, hold_undef = 0, 0, {5: 0, 10: 0}, 0
    for t in range(trials):
        rng = np.random.default_rng(t)
        idx = rng.permutation(len(y))
        Xtr, ytr = X[idx][:96], y[idx][:96]
        p5, r5, u5 = kfold_scores(None, Xtr, ytr, 5, t)
        p10, r10, u10 = kfold_scores(None, Xtr, ytr, 10, t)
        undef[5] += u5
        undef[10] += u10
        mean5_p.append(p5.mean())
        mean5_r.append(r5.mean())
        wider_std += (r10.std() > r5.std()) and (p10.std() > p5.std())
        wider_range += (np.ptp(r10) > np.ptp(r5)) and (np.ptp(p10) > np.ptp(p5))
        g10 = np.arange(96) % 10
        sal10 += [int(np.sum(ytr[g10 == i] == 1)) for i in range(10)]
        # one 76 / 20 split of the training data, as on the "1回分けるだけでは揺れる" slide
        inner = rng.permutation(96)
        Xf, yf, Xv, yv = Xtr[inner][:76], ytr[inner][:76], Xtr[inner][76:], ytr[inner][76:]
        sal_val.append(int(np.sum(yv == 1)))
        pred = DecisionTreeClassifier(random_state=t).fit(Xf, yf).predict(Xv)
        if np.sum(pred == 1) == 0 or np.sum(yv == 1) == 0:
            hold_undef += 1
            continue
        hp, hr = pr(yv, pred)
        hold_p.append(hp)
        hold_r.append(hr)
    print(f"   5-fold mean P : {spread(mean5_p)}  sd {np.std(mean5_p):.3f}")
    print(f"   5-fold mean R : {spread(mean5_r)}  sd {np.std(mean5_r):.3f}")
    print(f"   76/20 split P : {spread(hold_p)}  sd {np.std(hold_p):.3f}")
    print(f"   76/20 split R : {spread(hold_r)}  sd {np.std(hold_r):.3f}")
    print(f"   Salmon in the 20 validation fish: {spread(sal_val)}  mean {np.mean(sal_val):.2f}")
    print(f"   one missed Salmon at the median count moves Recall by 1/{int(np.median(sal_val))}"
          f" = {1 / np.median(sal_val):.3f}")
    print(f"   k=10 per-group sd > k=5 (both P and R): {wider_std / trials:.1%}")
    print(f"   k=10 per-group max-min > k=5 (both P and R): {wider_range / trials:.1%}")
    print(f"   group sizes k=5: {sorted(set(np.bincount(np.arange(96) % 5)))}"
          f"  k=10: {sorted(set(np.bincount(np.arange(96) % 10)))}")
    print(f"   Salmon per k=10 group: {spread(sal10)}")
    print(f"   undefined groups: k=5 {undef[5]} of {5 * trials}, k=10 {undef[10]} of {10 * trials},"
          f" 76/20 split {hold_undef} of {trials}")


if __name__ == "__main__":
    main()
