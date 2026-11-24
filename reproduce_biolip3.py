"""Reproduce the historical 37+33 BioLiP3 benchmark from frozen features."""
import argparse,csv,json,math,tempfile
from pathlib import Path
import numpy as np
from reproduce import ROOT,unpack,infer,source_archive,require,metrics,cindex
from reproduction.biolip3_assay import independent_y

URL="https://zhanggroup.org/BioLiP/lh_3affinity_data/00_Experiments/experiments_affinity.tsv"
SHA="c8467ed78b4e78889b417d752e8da4973bfd3a95fb5dc6f1244cafcc8249d0ab"
BUNDLE=ROOT/"reproduction/biolip3-replay.zip"
BUNDLE_SHA="85aecd9a195e5fa93046bfe20be49aa324cd673a9d14ee25a06f460d963ee607"
MODELS={"real":"DynaCPI-real-3D","shuffled":"DynaCPI-shuffled-3D","2d":"DynaCPI-calibrated-2D","hiq_only":"PerceiverCPI-original-HiQ349","perceiver":"PerceiverCPI-original-DAVIS45-HiQ349"}
PAIRS={"Dyna_REAL3D_minus_FullDAVISpretrainedOriginalPerceiver":("real","perceiver"),
       "Dyna_2D_minus_FullDAVISpretrainedOriginalPerceiver":("2d","perceiver"),
       "Dyna_REAL3D_minus_OriginalHiQ349onlyPerceiver":("real","hiq_only"),
       "Dyna_REAL3D_minus_Dyna_SHUFFLED3D":("real","shuffled")}

def read_labels(path,rows,n):
    lookup={r["line"]:i for i,r in enumerate(rows)}
    y=[None]*len(rows)
    with path.open(encoding="utf8",errors="replace",newline="") as f:
        rd=csv.reader(f,delimiter="\t")
        header=next(rd)
        require(len(header)==26 and header[13:17]==["affinity_manuals","affinity_binding_moads","affinity_pdbbind_cns","affinity_bindingdbs"],"BioLiP3 source schema mismatch")
        seen=set()
        for line,row in enumerate(rd,2):
            if line not in lookup:continue
            i=lookup[line];r=rows[i]
            require(len(row)==26 and row[0].strip().upper()==r["id"],"BioLiP3 row identity mismatch")
            seen.add(i)
            try:y[i]=independent_y(row,r["kind"])
            except AssertionError:
                if n==37:raise
    require(len(seen)==len(rows),"Some frozen rows missing")
    keep=np.array([i for i,v in enumerate(y) if v is not None],dtype=int)
    require(len(keep)==n,"Original accepted cohort count changed")
    return keep,np.array([y[i] for i in keep])

def ci(case,combined):
    rng=np.random.default_rng(20261116)
    idx=[rng.integers(0,len(y),size=(5000,len(y))) for y,_ in case]
    y=np.concatenate([labels[i] for (labels,_),i in zip(case,idx)],axis=1)
    m={}
    for mode in MODELS:
        p=np.concatenate([pred[mode][i] for (_,pred),i in zip(case,idx)],axis=1)
        mae=np.abs(p-y).mean(axis=1)
        c=np.array([cindex(a,b) for a,b in zip(y,p)])
        m[mode]=(mae,c)
    return {name:{"MAE_95pct_stratified_case_CI":np.quantile(m[a][0]-m[b][0],[.025,.975]).tolist(),
                  "Cindex_95pct_stratified_case_CI":np.quantile(m[a][1]-m[b][1],[.025,.975]).tolist()}
            for name,(a,b) in PAIRS.items()}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",type=Path,default=ROOT/"data/experiments_affinity.tsv",help="Original SHA-pinned BioLiP3 source file or download destination")
    ap.add_argument("--out",type=Path,default=ROOT/"runs/biolip3-reproduction.json")
    ap.add_argument("--inference-only",action="store_true")
    a=ap.parse_args()
    if a.out.exists() and not a.inference_only:ap.error("Output exists; use a new --out")
    with tempfile.TemporaryDirectory() as t:
        root=Path(t); ck=root/"model"; data=root/"data"
        unpack(ck);unpack(data,BUNDLE,BUNDLE_SHA)
        frozen=[]
        for i,n in enumerate((37,36)):
            d=data/f"cohort_{i}";ids,pred,parity=infer(ck,d,n)
            with np.load(d/"perceiver_reference.npz",allow_pickle=False) as z:
                require(np.array_equal(ids,z["ids"]),"Reference ID mismatch")
                pred["hiq_only"]=z["hiq_only"]
            rows=json.loads((d/"selection.json").read_text(encoding="utf8"))
            require([r["id"] for r in rows]==ids.tolist(),"Frozen cohort IDs mismatch")
            frozen.append((rows,pred,parity))
        if a.inference_only:
            print("PASS: 73 frozen input cases; no affinity data accessed.");return
        path=source_archive(a.source,URL,SHA,36087375)
        cases=[]
        for (rows,pred,_),n in zip(frozen,(37,33)):
            keep,y=read_labels(path,rows,n)
            cases.append((y,{m:pred[m][keep] for m in MODELS}))
        all_y=np.concatenate([y for y,_ in cases])
        all_pred={m:np.concatenate([p[m] for _,p in cases]) for m in MODELS}
        ref=json.loads((ROOT/"results/v28_full_davis_matched_perceiver.json").read_text(encoding="utf8"))
        results={};checks=0
        for name,(y,pred) in zip(("V21_37","V22_33","posthoc_pooled70"),[*cases,(all_y,all_pred)]):
            results[name]={}
            for mode,old in MODELS.items():
                v=metrics(y,pred[mode]);results[name][old]=v
                for metric,value in v.items():
                    if metric=="n":continue
                    expected=ref["models"][old][name][metric]
                    require(math.isclose(value,expected,rel_tol=0,abs_tol=1e-5),f"{name}/{mode}/{metric} mismatch: {value} != {expected}")
                    checks+=1
        boots=ci(cases,results);nci=0
        for name,items in boots.items():
            for key,value in items.items():
                require(np.allclose(value,ref["contrasts_predeclared_before_V28_completion"][name][key],rtol=0,atol=1e-5),f"{name}/{key} mismatch")
                nci+=1
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("x",encoding="utf8") as f:
            json.dump({"status":"PASS","metric_checks":checks,"bootstrap_interval_checks":nci,"prediction_parity":[p for _,_,p in frozen],"metrics":results,"confidence_intervals":boots,"scope":"Historical frozen-feature GeoFuse inference; Perceiver frozen outputs; post-hoc pooled70"},f,indent=2)
        for model,v in results["posthoc_pooled70"].items():
            print(f"{model:48s} RMSE {v['RMSE']:.6f}  CI {v['Cindex']:.6f}")
        print(f"PASS: {checks} metric entries, {nci} confidence intervals; report {a.out}")

if __name__=="__main__":main()
