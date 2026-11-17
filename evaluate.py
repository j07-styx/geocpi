"""Simple original-paper-compatible metric scorer on USER-SUPPLIED evaluation CSV.

Does not access any protected test. Run only after predictions were frozen
and the particular test labels are authorized to be opened.
"""
import argparse,csv,json
from pathlib import Path
import numpy as np
from scipy.stats import pearsonr,spearmanr

def cindex(y,p):
    """Same uncensored-lifelines concordance convention: true and predicted pAffinity larger=stronger."""
    n=len(y)
    i,j=np.triu_indices(n,k=1)
    valid=y[i]!=y[j]
    i,j=i[valid],j[valid]
    if not len(i):raise ValueError("No comparable target pairs")
    yt=np.sign(y[i]-y[j])
    pt=np.sign(p[i]-p[j])
    return float((np.count_nonzero(yt==pt)+0.5*np.count_nonzero(pt==0))/len(i))

def metrics(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float)
    if len(y)<3 or len(y)!=len(p) or not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError("Need at least three finite label/pred pairs")
    e=p-y;mse=float(np.mean(e**2))
    denom=float(np.sum((y-y.mean())**2))
    if denom<=0:raise ValueError("All target values equal; correlations undefined")
    return {"n":int(len(y)),"MSE":mse,"RMSE":float(np.sqrt(mse)),
      "MAE":float(np.mean(np.abs(e))),"R2":float(1-np.sum(e**2)/denom),
      "Cindex":cindex(y,p),"Pearson_r":float(pearsonr(y,p).statistic),
      "Spearman_rho":float(spearmanr(y,p).statistic)}

def load(path,value):
    with Path(path).open(encoding="utf8",newline="") as f:
        table=list(csv.DictReader(f))
    if not table or any("sample_id" not in r or value not in r for r in table):
        raise ValueError("Expected CSV columns sample_id and "+value)
    d={r["sample_id"]:float(r[value]) for r in table}
    if len(d)!=len(table) or not all(k for k in d):raise ValueError("Duplicate/missing IDs")
    return d

def main():
    ap=argparse.ArgumentParser(description="Score pre-frozen CPI predictions on aligned labels")
    ap.add_argument("--labels",required=True,help="local user-authorized CSV: sample_id,label")
    ap.add_argument("--predictions",required=True,help="frozen CSV: sample_id,prediction")
    ap.add_argument("--out",help="optional new aggregate JSON result; no individual labels")
    a=ap.parse_args()
    labels=load(a.labels,"label")
    pred=load(a.predictions,"prediction")
    if labels.keys()!=pred.keys():raise ValueError("Prediction and label sample-ID sets differ")
    ids=sorted(labels)
    result=metrics([labels[i] for i in ids],[pred[i] for i in ids])
    if a.out:
        output=Path(a.out)
        if output.exists():raise FileExistsError("Refuse to overwrite result")
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
