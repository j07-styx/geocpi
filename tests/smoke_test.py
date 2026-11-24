"""Entire prepared-feature train -> blind predict -> score CLI smoke test.

SYNTHETIC DATA ONLY. Not a benchmark, paper score, or model-quality claim.
"""
from pathlib import Path
import csv,json,subprocess,sys,tempfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable

def run(*args):
    cmd=[PY,str(ROOT/args[0]),*map(str,args[1:])]
    result=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stdout}\n{result.stderr}")
    print(result.stdout.strip())

def main():
    rng=np.random.default_rng(20261116)
    with tempfile.TemporaryDirectory(prefix="geofuse_cpi_synthetic_") as tmp:
        work=Path(tmp);n=80;m=12
        x=rng.standard_normal((n,423)).astype(np.float32)
        geom={mode:rng.standard_normal((n,704)).astype(np.float32) for mode in ("real","shuffled","pocket")}
        y=(7.3+.14*x[:,0]-.08*x[:,7]+rng.standard_normal(n)*.35).astype(np.float64)
        source=work/"train.npz"
        np.savez_compressed(source,x2d=x,y=y,groups=np.arange(n)%20,**geom)
        unseen=work/"blind.npz"
        np.savez_compressed(unseen,x2d=x[:m],ids=np.array([f"synthetic_{i:02d}" for i in range(m)]),
                            **{key:value[:m] for key,value in geom.items()})
        folder=work/"trained";pred=work/"pred.csv"
        run("train.py","--data",source,"--out",folder,"--epochs","1","--folds","2","--inner","2")
        run("predict.py","--data",unseen,"--checkpoint",folder,"--out",pred)
        with (work/"labels.csv").open("w",newline="",encoding="utf8") as f:
            cw=csv.writer(f);cw.writerow(["sample_id","label"])
            for i in range(m):cw.writerow([f"synthetic_{i:02d}",y[i]])
        run("evaluate.py","--labels",work/"labels.csv","--predictions",pred,
            "--out",work/"metrics.json")
        result=json.loads((work/"metrics.json").read_text())
        assert result["n"]==m and np.isfinite(result["RMSE"])
        run("verify.py")
    print("PASS: synthetic train -> blind predict -> evaluation; no experimental affinity opened")

if __name__=="__main__":
    main()
