"""Inference on prepared 423D DAVIS-v5 backbone and 704D native-bound geometry.

This accepts precomputed features, NOT raw SMILES/PDB; see README for the exact
input contract. Only load trusted local checkpoints (joblib uses pickle).
No affinity outcomes are needed or allowed during inference.
"""
import argparse,csv,json,sys
from pathlib import Path
import joblib,numpy as np,torch
sys.path.insert(0,str(Path(__file__).resolve().parent/"src"))
from geofuse_cpi import ExplicitPairResidual

def main():
    p=argparse.ArgumentParser(description="GeoFuse-CPI 3D prepared-feature inference")
    p.add_argument("--data",required=True,help="label-free npz: x2d,real,shuffled,pocket,optional ids")
    p.add_argument("--checkpoint",required=True,help="trusted local run folder created by train.py")
    p.add_argument("--out",required=True,help="new CSV path; refuse overwrites")
    p.add_argument("--mode",choices=("real","shuffled","pocket","2d"),default="real")
    args=p.parse_args()
    out=Path(args.out)
    if out.exists():raise FileExistsError("Refuse to overwrite predictions: "+str(out))
    ck=Path(args.checkpoint)
    manifest=json.loads((ck/"run.json").read_text(encoding="utf8"))
    if manifest["status"]!="SOURCE_TRAIN_ONLY_COMPLETE_NOT_EXTERNAL_TEST":
        raise ValueError("Unrecognized checkpoint run status")
    torch.set_num_threads(3)
    with np.load(args.data,allow_pickle=False) as z:
        if "y" in z.files or "label" in z.files:
            raise ValueError("Inference source must be label-free; no Y fields accepted")
        x=z["x2d"].astype(np.float32)
        if x.ndim!=2 or x.shape[1]!=423:raise ValueError("Require x2d (N,423)")
        v=z[args.mode].astype(np.float64) if args.mode!="2d" else None
        ids=z["ids"].astype(str) if "ids" in z.files else np.arange(len(x)).astype(str)
    if len(ids)!=len(x) or len(set(ids))!=len(x):
        raise ValueError("Example IDs must be unique and aligned")
    if not np.isfinite(x).all() or (v is not None and (v.shape!=(len(x),704) or not np.isfinite(v).all())):
        raise ValueError("Nonfinite or malformed inference features")
    preds=[]
    for fold in range(manifest["folds"]):
        root=ck/f"fold_{fold}"
        calibrators=joblib.load(root/"calibrators.joblib")
        if len(calibrators)!=3:raise ValueError("Expected exactly three 2D calibrators per source fold")
        base=np.mean([m.predict(x) for m in calibrators],axis=0)
        if args.mode=="2d":
            preds.append(base)
            continue
        with np.load(root/f"{args.mode}_norm.npz",allow_pickle=False) as z:
            mean=z["mean"];std=z["std"];scale=float(z["scale"])
        zinput=torch.from_numpy(((v-mean)/std).astype(np.float32))
        model=ExplicitPairResidual()
        model.load_state_dict(torch.load(root/f"{args.mode}.pt",map_location="cpu",weights_only=True))
        model.eval()
        with torch.no_grad():
            pred=base+scale*model(zinput).numpy().astype(float)
        preds.append(pred)
    final=np.mean(preds,axis=0)
    if not np.isfinite(final).all():raise ValueError("Nonfinite predictions")
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x",newline="",encoding="utf8") as f:
        cw=csv.writer(f);cw.writerow(["sample_id","prediction"])
        cw.writerows(zip(ids,final))
    print(f"Wrote {len(final)} label-free predictions to {out} (mode={args.mode})")

if __name__=="__main__":
    main()
