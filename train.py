"""Train the V17 DynaCPI native-geometry head on PREPARED, TRAIN-only features.

Input npz: x2d (N,423), real/shuffled/pocket (N,704), groups (N,), y (N,).
Optional --splits NPZ: fit_0,dev_0,...,fit_3,dev_3 pre-frozen source roles.
The ORIGINAL historical V17 results used existing source roles and DAVIS-v5
backbone features; generic GroupKFold is for NEW development, not a bit-identical
reproduction of that historical split.

Absolutely no hidden benchmark Y, raw BioLiP3 assay data or external outcomes.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import joblib
import numpy as np
import torch
from sklearn.model_selection import GroupKFold
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from dynacpi3d import ExplicitPairResidual, make_calibrator

SEEDS = (2931, 2932, 2933)
MODES = ("real", "shuffled", "pocket")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def validate(data):
    required = ("x2d", "real", "shuffled", "pocket", "groups", "y")
    if not all(key in data for key in required):
        raise ValueError("Missing required training arrays: " + ", ".join(required))
    x = data["x2d"].astype(np.float32)
    geometries = {k: data[k].astype(np.float32) for k in MODES}
    y = data["y"].astype(np.float64)
    group = data["groups"]
    n = len(y)
    if x.shape != (n, 423) or any(v.shape != (n, 704) for v in geometries.values()):
        raise ValueError("Expected x2d=(N,423), 3 geometries=(N,704), y=(N,)")
    if len(group) != n or n < 16:
        raise ValueError("Need >=16 examples and exactly one group ID per example")
    if not (np.isfinite(x).all() and np.isfinite(y).all()
            and all(np.isfinite(v).all() for v in geometries.values())):
        raise ValueError("Nonfinite feature or label")
    if len(set(map(str, group))) < 4:
        raise ValueError("Need four distinct protein groups")
    return x, geometries, y, group


def get_splits(data, groups, count):
    if data is None:
        return list(GroupKFold(n_splits=count).split(np.arange(len(groups)), groups=groups))
    pairs = []
    for i in range(count):
        fit = data[f"fit_{i}"].astype(int)
        dev = data[f"dev_{i}"].astype(int)
        pairs.append((fit, dev))
    held = np.concatenate([dev for _, dev in pairs])
    if not np.array_equal(np.sort(held), np.arange(len(groups))):
        raise ValueError("Frozen DEV rows must partition training-source examples exactly once")
    for fit, dev in pairs:
        if not len(fit) or not len(dev) or np.any(fit < 0) or np.any(dev < 0):
            raise ValueError("Empty or invalid source fold")
        if (set(fit) & set(dev)) or (set(groups[fit]) & set(groups[dev])):
            raise ValueError("Protein-group leakage across FIT and DEV")
        if len(set(groups[fit])) < 3:
            raise ValueError("FIT split has too few groups for inner OOF")
    return pairs


def main():
    ap = argparse.ArgumentParser(description="V17 source-only fourfold 2D+704D residual trainer")
    ap.add_argument("--data", required=True, help="TRAIN-only prepared NPZ; NEVER protected tests")
    ap.add_argument("--out", required=True, help="New directory; will not overwrite an existing run")
    ap.add_argument("--splits", help="Original fixed source fold NPZ (recommended for historical work)")
    ap.add_argument("--epochs", type=int, default=16)
    ap.add_argument("--folds", type=int, default=4)
    ap.add_argument("--inner", type=int, default=3)
    args = ap.parse_args()
    if args.epochs < 1 or args.folds < 2 or args.inner < 2:
        ap.error("epochs >=1, folds >=2, inner >=2")
    out = Path(args.out).resolve()
    if out.exists():
        raise FileExistsError("Refusing to overwrite a model run: " + str(out))
    with np.load(args.data, allow_pickle=False) as data:
        x, geo, y, groups = validate(data)
    if args.splits:
        with np.load(args.splits, allow_pickle=False) as splitfile:
            folds = get_splits(splitfile, groups, args.folds)
    else:
        folds = get_splits(None, groups, args.folds)
    torch.set_num_threads(3)
    out.mkdir(parents=True, exist_ok=False)
    fold_results = []
    for i, (fit, dev) in enumerate(folds):
        if set(groups[fit]) & set(groups[dev]):
            raise ValueError("Source FIT/DEV protein family leak")
        foldpath = out / f"fold_{i}"
        foldpath.mkdir()
        # Inner group-heldout 2D estimates avoid artificially optimistic training residuals.
        inners = GroupKFold(n_splits=args.inner)
        inner_pred = np.full(len(fit), np.nan, dtype=float)
        for tri, vii in inners.split(x[fit], y[fit], groups[fit]):
            preds = []
            for seed in SEEDS:
                m = make_calibrator(seed)
                m.fit(x[fit[tri]], y[fit[tri]])
                preds.append(m.predict(x[fit[vii]]))
            inner_pred[vii] = np.mean(preds, axis=0)
        if not np.isfinite(inner_pred).all():
            raise ValueError("Inner OOF source residual target is incomplete")
        calibrators = []
        for seed in SEEDS:
            m = make_calibrator(seed)
            m.fit(x[fit], y[fit])
            calibrators.append(m)
        joblib.dump(calibrators, foldpath / "calibrators.joblib")
        base = np.mean([m.predict(x[dev]) for m in calibrators], axis=0)
        scale = float(y[fit].std())
        if scale <= 1e-8:
            raise ValueError("Source training label variance too small")
        target = torch.from_numpy(((y[fit] - inner_pred) / scale).astype(np.float32))
        predictions = {}
        for mode in MODES:
            v = geo[mode].astype(np.float64)
            mean = v[fit].mean(axis=0)
            std = np.maximum(v[fit].std(axis=0), 0.05)
            ztrain = torch.from_numpy(((v[fit] - mean) / std).astype(np.float32))
            zdev = torch.from_numpy(((v[dev] - mean) / std).astype(np.float32))
            torch.manual_seed(20261116 + i * 101)
            model = ExplicitPairResidual()
            model.train()
            optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.002)
            for epoch in range(args.epochs):
                indices = np.random.default_rng(20261116 + i * 101 + epoch).permutation(len(fit))
                for start in range(0, len(fit), 32):
                    idx = torch.from_numpy(indices[start:start + 32].astype(np.int64))
                    optimizer.zero_grad(set_to_none=True)
                    loss = ((model(ztrain[idx]) - target[idx]) ** 2).mean()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                    optimizer.step()
            model.eval()
            with torch.no_grad():
                predictions[mode] = base + scale * model(zdev).numpy().astype(float)
            torch.save(model.state_dict(), foldpath / f"{mode}.pt")
            np.savez_compressed(foldpath / f"{mode}_norm.npz", mean=mean, std=std, scale=scale)
        fold_results.append({"fold": i, "fit_count": len(fit), "source_dev_count": len(dev),
                             "source_fit_groups": len(set(groups[fit])),
                             "source_dev_groups": len(set(groups[dev])),
                             "real_oof_source_RMSE": float(np.sqrt(np.mean((predictions["real"] - y[dev]) ** 2)))})
        print(f"Finished TRAIN-only fold {i + 1}/{len(folds)}", flush=True)
    manifest = {
        "status": "SOURCE_TRAIN_ONLY_COMPLETE_NOT_EXTERNAL_TEST",
        "feature_input_sha256": sha(args.data),
        "split_file_sha256": sha(args.splits) if args.splits else None,
        "split_mode": "fixed_source" if args.splits else "NEW_GroupKFold_NOT_ORIGINAL_V17_SPLITS",
        "seeds": list(SEEDS), "epochs": args.epochs, "folds": args.folds,
        "inner_group_folds": args.inner, "n_source": len(y), "fold_summaries": fold_results,
        "caution": "Source DEV was used for reports; no new blinded test evaluated.",
    }
    (out / "run.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Source training complete:", out)


if __name__ == "__main__":
    main()
