# Trains the two course networks exactly as the decks do and dumps weights,
# training snapshots, and sample images for the interactive NN explorer
# (explorer/index.html). Also prints the measured facts that go into
# doc/course-arc.md §実測ログ (never write a number on a slide that was not
# printed by this script or by the deck itself).
#
#   moons : nn-numpy.qmd    — 2-16-1 MLP, full batch, lr 0.5, 4000 iters, rng(0)
#   mnist : mnist-project.qmd — Flatten/Linear(784,128)/ReLU/Linear(128,10),
#                               Adam lr 1e-3, batch 128 shuffle, 3 epochs, seed 0
#
# Usage: python tools/explorer_export.py    (from the repo root)
#        -> writes explorer/data_ai.js, prints measured facts to stdout

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.datasets import make_moons
from torchvision import datasets, transforms

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "explorer" / "data_ai.js"

ND = 4  # decimals kept in the export (accuracy of the rounded net is verified below)


def rf(x, nd=ND):
    return round(float(x), nd)


def rl(a, nd=ND):
    return [round(float(v), nd) for v in np.asarray(a).ravel()]


# ---------------------------------------------------------------- moons ----
# Mirrors nn-numpy.qmd line for line (forward / backward / training loop).

def forward(X, W1, b1, w2, c2):
    Z = X @ W1 + b1
    H = np.maximum(0, Z)
    u = H @ w2 + c2
    p = 1 / (1 + np.exp(-u))
    return Z, H, u, p


def backward(X, y, Z, H, w2, p):
    N = len(X)
    delta_out = (p - y) / N
    g_w2 = H.T @ delta_out
    g_c2 = delta_out.sum()
    D_mid = np.outer(delta_out, w2) * (Z > 0)
    g_W1 = X.T @ D_mid
    g_b1 = D_mid.sum(axis=0)
    return g_W1, g_b1, g_w2, g_c2


def loss_acc(X, y, W1, b1, w2, c2):
    _, _, _, p = forward(X, W1, b1, w2, c2)
    eps = 1e-10
    loss = -np.mean(y * np.log(np.clip(p, eps, 1)) +
                    (1 - y) * np.log(np.clip(1 - p, eps, 1)))
    acc = np.mean((p >= 0.5) == y)
    return float(loss), float(acc)


def export_moons():
    X, y = make_moons(n_samples=200, noise=0.1, random_state=42)

    rng = np.random.default_rng(0)
    hidden = 16
    W1 = rng.normal(0, 1.0, (2, hidden))
    b1 = np.zeros(hidden)
    w2 = rng.normal(0, 1.0, hidden)
    c2 = 0.0
    lr = 0.5

    snap_at = [0, 1, 10, 50, 100, 500, 1000, 2000, 4000]
    snapshots = []
    curve = {"it": [], "loss": [], "acc": []}

    def snap(i):
        loss, acc = loss_acc(X, y, W1, b1, w2, c2)
        snapshots.append({
            "it": i, "loss": rf(loss), "acc": rf(acc),
            "W1": rl(W1), "b1": rl(b1), "w2": rl(w2), "c2": rf(c2),
        })

    snap(0)
    for i in range(1, 4001):
        Z, H, u, p = forward(X, W1, b1, w2, c2)
        g_W1, g_b1, g_w2, g_c2 = backward(X, y, Z, H, w2, p)
        W1 -= lr * g_W1
        b1 -= lr * g_b1
        w2 -= lr * g_w2
        c2 -= lr * g_c2
        if i in snap_at:
            snap(i)
        if i % 20 == 0 or i == 1:
            loss, acc = loss_acc(X, y, W1, b1, w2, c2)
            curve["it"].append(i)
            curve["loss"].append(rf(loss))
            curve["acc"].append(rf(acc))

    print("[moons] snapshots (it, loss, acc):")
    for s in snapshots:
        print(f"  it={s['it']:5d}  loss={s['loss']:.4f}  acc={s['acc']:.1%}")

    return {
        "hidden": hidden,
        "X": [[rf(a), rf(b)] for a, b in X],
        "y": [int(v) for v in y],
        "snapshots": snapshots,
        "curve": curve,
    }


# ---------------------------------------------------------------- mnist ----
# Mirrors mnist-project.qmd: same seed, same construction order, so the
# exported weights equal the ones the deck trains at render time.

def export_mnist():
    transform = transforms.ToTensor()
    train_ds = datasets.MNIST(root=ROOT / "data", train=True, download=True, transform=transform)
    test_ds = datasets.MNIST(root=ROOT / "data", train=False, download=True, transform=transform)

    torch.manual_seed(0)
    model = nn.Sequential(
        nn.Flatten(),
        nn.Linear(784, 128),
        nn.ReLU(),
        nn.Linear(128, 10),
    )

    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=128, shuffle=True)
    test_loader = torch.utils.data.DataLoader(test_ds, batch_size=1000)

    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    for epoch in range(1, 4):
        for x_batch, y_batch in train_loader:
            optimizer.zero_grad()
            loss = loss_fn(model(x_batch), y_batch)
            loss.backward()
            optimizer.step()
        correct = 0
        with torch.no_grad():
            for x_batch, y_batch in test_loader:
                correct += (model(x_batch).argmax(dim=1) == y_batch).sum().item()
        print(f"[mnist] epoch {epoch} | test acc: {correct / len(test_ds):.2%}")

    # full-precision predictions over the whole test set
    with torch.no_grad():
        X_test = torch.stack([img for img, _ in test_ds])       # (10000, 1, 28, 28)
        y_test = torch.tensor([lab for _, lab in test_ds])
        logits = model(X_test)
        probs = torch.softmax(logits, dim=1)
        preds = logits.argmax(dim=1)
    acc_full = (preds == y_test).float().mean().item()

    # confusion pairs and most confident mistakes (measured facts for the deck)
    conf = torch.zeros(10, 10, dtype=torch.int64)
    for t, p in zip(y_test, preds):
        conf[t, p] += 1
    pairs = [(conf[t, p].item(), t, p) for t in range(10) for p in range(10) if t != p]
    pairs.sort(reverse=True)
    print("[mnist] top confusion pairs (count, true->pred):")
    for c, t, p in pairs[:6]:
        print(f"  {c:3d}  {t} -> {p}")

    wrong = (preds != y_test).nonzero().squeeze(1)
    wrong_conf = probs[wrong, preds[wrong]]
    order = wrong_conf.argsort(descending=True)
    print("[mnist] most confident mistakes (p, true->pred, test idx):")
    for k in order[:6]:
        i = wrong[k].item()
        print(f"  p={wrong_conf[k].item():.3f}  {y_test[i].item()} -> {preds[i].item()}  idx={i}")

    # rounded weights (what the explorer ships) — verify the rounding is free
    W1 = model[1].weight.detach().numpy().round(ND)   # (128, 784)
    b1 = model[1].bias.detach().numpy().round(ND)
    W2 = model[3].weight.detach().numpy().round(ND)   # (10, 128)
    b2 = model[3].bias.detach().numpy().round(ND)
    Xf = X_test.numpy().reshape(-1, 784)
    H = np.maximum(0, Xf @ W1.T + b1)
    preds_r = (H @ W2.T + b2).argmax(axis=1)
    acc_round = (preds_r == y_test.numpy()).mean()
    print(f"[mnist] test acc full={acc_full:.4f}  rounded({ND}dp)={acc_round:.4f}")
    if abs(acc_full - acc_round) > 0.001:
        raise RuntimeError("rounding changed accuracy — increase ND")

    # sample strip for the draw view: one correct per digit + 6 misreads
    samples = []
    for d in range(10):
        i = next(i for i in range(len(test_ds))
                 if y_test[i].item() == d and preds[i].item() == d)
        samples.append(i)
    samples += [wrong[k].item() for k in order[:6]]
    sample_dump = [{
        "px": [int(v) for v in (Xf[i] * 255).round()],
        "label": int(y_test[i]), "pred": int(preds[i]),
    } for i in samples]

    return {
        "shape": [784, 128, 10],
        "test_acc": rf(acc_full),
        "W1": rl(W1), "b1": rl(b1), "W2": rl(W2), "b2": rl(b2),
        "samples": sample_dump,
    }


def main():
    data = {"moons": export_moons(), "mnist": export_mnist()}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("window.EXPLORER_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
                   encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
