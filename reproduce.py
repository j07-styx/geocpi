"""Recompute OpenBind 482 benchmark from frozen features and trained models.

No training labels or test affinities are included in the replay bundle.
The public experimental archive is downloaded independently and SHA-pinned.
The Perceiver baseline is replayed from its frozen ensemble outputs.
"""
import argparse, collections, csv, hashlib, json, math, sys, tempfile, urllib.request, zipfile
from pathlib import Path
import numpy as np
import lightgbm as lgb
import torch
from evaluate import metrics, cindex
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from geofuse_cpi import ExplicitPairResidual

ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "reproduction/openbind-replay.zip"
BUNDLE_SHA = "3dc945c3e68d9459319460f32115ede09688fb1b692b97c4f12baba3c09d9984"
SOURCE_URL = "https://zenodo.org/records/22142262/files/OpenBind_EV-A71_2A.zip?download=1"
SOURCE_SHA = "e0d2e38eddf75ebf4247aff0fe28ae15dfa25ecb30deeb4cf950ae184b304a25"
ARMS = {"raw": "raw_DAVIS_v5", "2d": "calibrated_original_DynaV5_2D",
        "real": "original_DynaV5_plus_REAL_native_pair_geom",
        "shuffled": "original_DynaV5_plus_SHUFFLED_native_pair_geom",
        "pocket": "original_DynaV5_plus_POCKET_only",
        "perceiver": "original_full12_DAVISpretrained_Perceiver_ensemble"}
CONTRASTS = {"REAL_minus_SHUFFLED": "shuffled", "REAL_minus_POCKET": "pocket",
             "REAL_minus_calibrated_2D": "2d", "REAL_minus_full12_original_Perceiver": "perceiver"}

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def source_archive(path, url=SOURCE_URL, expected_sha=SOURCE_SHA, size=124498453):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(".download")
        print("Downloading pinned original dataset...", flush=True)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "GeoFuse-CPI-reproduction/1.0"}), timeout=90) as response, part.open("wb") as f:
                while block := response.read(1 << 20):
                    f.write(block)
                    require(f.tell() <= size, "Unexpected archive size")
            require(sha(part) == expected_sha, "Downloaded archive SHA mismatch")
            part.replace(path)
        finally:
            if part.exists():
                part.unlink()
    require(sha(path) == expected_sha, "Original source archive SHA mismatch")
    return path

def unpack(destination, archive=BUNDLE, expected_sha=BUNDLE_SHA):
    require(sha(archive) == expected_sha, "Replay bundle SHA mismatch")
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read("manifest.json"))
        for name, expected in manifest["files"].items():
            p = destination / name
            require(p.resolve().is_relative_to(destination.resolve()), "Invalid bundle path")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(z.read(name))
            require(sha(p) == expected, "Artifact SHA mismatch: " + name)

def infer(bundle, data=None, n=660):
    data = bundle if data is None else data
    torch.set_num_threads(3)
    with np.load(data / "features.npz", allow_pickle=False) as z:
        require(set(z.files) == {"ids", "x2d", "real", "shuffled", "pocket"}, "Unexpected input fields")
        ids, x = z["ids"], z["x2d"].astype(np.float32)
        geos = {m: z[m].astype(np.float64) for m in ("real", "shuffled", "pocket")}
    require(x.shape == (n, 423) and len(set(ids)) == n, "Invalid features")
    require(np.isfinite(x).all() and all(v.shape == (n,704) and np.isfinite(v).all() for v in geos.values()), "Invalid geometry")
    folds = {m: [] for m in ("2d", *geos)}
    for i in range(4):
        d = bundle / f"fold_{i}"
        base = np.mean([lgb.Booster(model_file=str(d / f"calibrator_{j}.txt")).predict(x, num_threads=3) for j in range(3)], axis=0)
        folds["2d"].append(base)
        for mode, v in geos.items():
            with np.load(d / f"{mode}_norm.npz", allow_pickle=False) as z:
                inputs = torch.from_numpy(((v - z["mean"]) / z["std"]).astype(np.float32))
                scale = float(z["scale"])
            net = ExplicitPairResidual()
            net.load_state_dict(torch.load(d / f"{mode}.pt", map_location="cpu", weights_only=True))
            net.eval()
            with torch.no_grad():
                folds[mode].append(base + scale * net(inputs).numpy().astype(float))
    predictions = {m: np.mean(v, axis=0) for m,v in folds.items()}
    predictions["raw"] = x[:, -1].astype(float)
    with np.load(data / "perceiver_reference.npz", allow_pickle=False) as z:
        require(np.array_equal(z["ids"], ids), "Comparator IDs differ")
        predictions["perceiver"] = z["prediction"]
    with np.load(data / "frozen_reference.npz", allow_pickle=False) as z:
        require(np.array_equal(z["ids"], ids), "Reference IDs differ")
        parity = {m: float(np.max(np.abs(p - z[ARMS[m]]))) for m,p in predictions.items() if m != "perceiver"}
    print("Maximum absolute prediction differences:", parity, flush=True)
    require(max(parity.values()) <= 1e-5, "Frozen prediction parity failed")
    return ids, predictions, parity

def labels(bundle, archive, ids):
    rows = json.loads((bundle / "selection.json").read_text(encoding="utf8"))
    require([r["id"] for r in rows] == ids.tolist(), "Frozen selection IDs differ")
    by_group = collections.defaultdict(list)
    events = {}
    with zipfile.ZipFile(archive) as z, z.open("OpenBind_EV-A71_2A/EV-A71_2A_metadata.csv") as f:
        records = list(csv.DictReader(line.decode("utf8", "replace") for line in f))
    require(len(records) == 925, "Unexpected metadata count")
    for row in records:
        events[row["complex_name"]] = row["compound_group"]
        try:
            v = float(row["experimental_pKD"])
        except (TypeError, ValueError):
            continue
        if np.isfinite(v):
            by_group[row["compound_group"]].append(v)
    for r in rows:
        require(events.get(r["id"]) == r["compound_group"], "Source event alignment mismatch")
    keep = np.array([i for i,r in enumerate(rows) if by_group[r["compound_group"]]], dtype=int)
    y = np.array([np.median(by_group[rows[i]["compound_group"]]) for i in keep])
    scaff = np.array([rows[i]["scaffold"] for i in keep])
    require(len(keep) == 482 and len(np.unique(scaff)) == 264, "Cohort/scaffold counts differ")
    return keep, y, scaff

def bootstrap(y, pred, scaff):
    _, gi = np.unique(scaff, return_inverse=True)
    n = int(gi.max()) + 1
    rng = np.random.default_rng(20261117)
    draws = rng.integers(0,n,size=(5000,n))
    M = np.zeros((5000,n),dtype=float)
    np.add.at(M,(np.repeat(np.arange(5000),n),draws.ravel()),1)
    count = M @ np.bincount(gi,minlength=n)
    i,j = np.triu_indices(len(y),1)
    keep = y[i] != y[j]
    i,j = i[keep],j[keep]
    a,b = gi[i],gi[j]
    off = a != b
    D = np.zeros((n,n),dtype=float)
    np.add.at(D,(a,b),np.where(off,.5,1.))
    np.add.at(D,(b[off],a[off]),.5)
    den = np.sum((M @ D)*M,axis=1)
    require(np.all(den > 0), "Bootstrap has no comparable pairs")
    values = {}
    for name,p in pred.items():
        if name == "raw":
            continue
        K = np.zeros((n,n),dtype=float)
        signs = np.sign(p[i]-p[j])
        wins = np.where(signs == 0,.5,(signs == np.sign(y[i]-y[j])).astype(float))
        np.add.at(K,(a,b),np.where(off,wins*.5,wins))
        np.add.at(K,(b[off],a[off]),wins[off]*.5)
        concordance = np.sum((M@K)*M,axis=1)/den
        mae = M@np.bincount(gi,weights=np.abs(p-y),minlength=n)/count
        rmse = np.sqrt(M@np.bincount(gi,weights=(p-y)**2,minlength=n)/count)
        values[name] = (mae,rmse,concordance)
    return {name:{k: np.quantile(a-b,[.025,.975]).tolist()
                  for k,a,b in zip(("MAE_delta_95pct_CI","RMSE_delta_95pct_CI","Cindex_delta_95pct_CI"),values["real"],values[other])}
            for name,other in CONTRASTS.items()}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, default=ROOT/"data/OpenBind_EV-A71_2A.zip", help="Existing verified archive or download destination")
    p.add_argument("--out", type=Path, default=ROOT/"runs/openbind-reproduction.json")
    p.add_argument("--inference-only", action="store_true", help="Check 660 frozen predictions without downloading or accessing labels")
    args = p.parse_args()
    if args.out.exists() and not args.inference_only:
        p.error("Output already exists; choose another --out")
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp)
        unpack(bundle)
        ids, predictions, parity = infer(bundle)
        if args.inference_only:
            print("PASS: 660 real model predictions per arm; no labels accessed.")
            return
        archive = source_archive(args.archive)
        keep,y,scaff = labels(bundle, archive, ids)
        pred = {k:v[keep] for k,v in predictions.items()}
        got = {ARMS[k]:dict(metrics(y,v),mean_prediction=float(v.mean()),mean_observed_pKD=float(y.mean())) for k,v in pred.items()}
        expected = json.loads((ROOT/"results/openbind2026_single_target_482_aggregate.json").read_text(encoding="utf8"))
        checks = 0
        for arm, result in got.items():
            for key,value in result.items():
                ref = expected["scored_model_original_source_frozen"][arm][key]
                require(math.isclose(value,ref,rel_tol=0,abs_tol=1e-5),f"Metric mismatch {arm}/{key}: {value} vs {ref}")
                checks += 1
        boots = bootstrap(y,pred,scaff)
        ci_checks = 0
        for name,vals in boots.items():
            for key,value in vals.items():
                ref = expected["four_fixed_paired_descriptive_scaffold_cluster_5000boot"][name][key]
                require(np.allclose(value,ref,rtol=0,atol=1e-5),f"Interval mismatch {name}/{key}")
                ci_checks += 1
        result = {"status":"PASS","n":len(y),"scaffold_clusters":len(set(scaff)),
                  "prediction_parity_max_abs":parity,"metric_checks":checks,"bootstrap_interval_checks":ci_checks,
                  "metrics":got,"confidence_intervals":boots,
                  "scope":"Historical prepared-feature inference; frozen Perceiver outputs, not independently retrained"}
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("x",encoding="utf8") as f:
            json.dump(result,f,indent=2)
        for arm,v in got.items():
            print(f"{arm:52s} RMSE {v['RMSE']:.6f}  CI {v['Cindex']:.6f}")
        print(f"PASS: {checks} metric entries, {ci_checks} confidence intervals; report {args.out}")

if __name__ == "__main__":
    main()
