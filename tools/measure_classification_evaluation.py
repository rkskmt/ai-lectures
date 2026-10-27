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


if __name__ == "__main__":
    main()
