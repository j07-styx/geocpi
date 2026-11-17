"""End-to-end frozen DynaCPI v5 + native 3D inference from raw SDF/PDB/SMILES.

Example:
python predict_raw.py --manifest private/raw_cases.csv \
 --esm-checkpoint C:/.../esm2_t33_650M_UR50D.pt \
 --davis-ligands C:/.../ligands_can.txt \
 --davis-model-2931 C:/.../centered_esm_mse_seed2931.pt \
 --davis-model-2932 C:/.../centered_esm_mse_seed2932.pt \
 --trained-residuals runs/v48_train349_source_fourfold_replay \
 --out runs/new_native_predictions.csv --features-out private/raw_features_noY.npz

Requires experimentally native bound ligand coordinates in supplied structure.
Never loads or outputs numeric affinities/targets from its inputs.
"""
import argparse,csv,hashlib,json,sys
from pathlib import Path
import numpy as np,torch,joblib
from rdkit import Chem
sys.path.insert(0,str(Path(__file__).resolve().parent/"src"))
from dynacpi3d.model import ExplicitPairResidual
from dynacpi3d.raw_features import graph_from_raw,esm_mean,backbone_context,side_features,sha
ARMS=("real","shuffled","pocket")
FORBIDDEN={"label","y","pkd","pki","affinity","experimental_pkd",
 "experimental_kd","kd","ki","binding_affinity","target"}
REQUIRED={"sample_id","smiles","ligand_sdf","complex_pdb"}
def read_inputs(path):
 path=Path(path).resolve()
 with path.open(encoding="utf8",newline="") as f:
  reader=csv.DictReader(f)
  if not reader.fieldnames:raise ValueError("No CSV header")
  names={x.strip().lower() for x in reader.fieldnames}
  if REQUIRED.difference(names):raise ValueError("Input must have "+", ".join(sorted(REQUIRED)))
  if FORBIDDEN.intersection(names):
   raise ValueError("Raw inference is label-blind: remove numerical assay columns")
  if len(names)!=len(reader.fieldnames):
   raise ValueError("Duplicated input columns")
  rows=list(reader)
 if not rows:raise ValueError("Need at least one complex")
 ids=[r["sample_id"].strip() for r in rows]
 if not all(ids) or len(ids)!=len(set(ids)):raise ValueError("Duplicate/blank IDs")
 result=[]
 for row in rows:
  if not all(row.get(k,"").strip() for k in REQUIRED):
   raise ValueError("One or more required CSV fields are blank")
  typ=row.get("assay_type","KD").strip().upper()
  if typ not in ("KD","KI"):raise ValueError("assay_type must be KD or KI")
  result.append({"sample_id":row["sample_id"].strip(),
   "smiles":row["smiles"].strip(),"assay_type":typ,
   "ligand_sdf":str((path.parent/row["ligand_sdf"]).resolve()),
   "complex_pdb":str((path.parent/row["complex_pdb"]).resolve()),
   "receptor_chain":row.get("receptor_chain","").strip(),
   "sequence":row.get("sequence","").strip()})
 return result
def load_source_fitted_3d(checkpoint,x2d,geom):
 """Exactly the original V17 4×3 LightGBM and 4×3 bounded-residual arms."""
 run=json.loads((checkpoint/"run.json").read_text(encoding="utf8"))
 if run["status"]!="SOURCE_TRAIN_ONLY_COMPLETE_NOT_EXTERNAL_TEST":
  raise ValueError("Source-only trained checkpoint manifest not recognized")
 folds=run["folds"]
 if folds!=4:raise ValueError("The published original V17 architecture uses 4 source folds")
 outputs={name:[] for name in ("calibrated_2d","real_3d","shuffled_3d","pocket_only")}
 torch.set_num_threads(3)
 for fold in range(folds):
  folder=checkpoint/f"fold_{fold}"
  calibrators=joblib.load(folder/"calibrators.joblib")
  if len(calibrators)!=3:raise ValueError("Expected 3 source-fitted LightGBM members")
  base=np.mean([m.predict(x2d) for m in calibrators],axis=0)
  outputs["calibrated_2d"].append(base)
  for mode,name in (("real","real_3d"),("shuffled","shuffled_3d"),("pocket","pocket_only")):
   with np.load(folder/(mode+"_norm.npz"),allow_pickle=False) as norm:
    mean=norm["mean"];std=norm["std"];scale=float(norm["scale"])
   z=torch.from_numpy(((geom[mode]-mean)/std).astype(np.float32))
   model=ExplicitPairResidual().eval()
   state=torch.load(folder/(mode+".pt"),map_location="cpu",weights_only=True)
   model.load_state_dict(state)
   with torch.no_grad():outputs[name].append(base+scale*model(z).numpy().astype(float))
 return {k:np.mean(v,axis=0) for k,v in outputs.items()}
def main():
 ap=argparse.ArgumentParser(description="Raw-native-bound original DynaCPI v5 + REAL 3D/SHUFFLED/POCKET inference")
 ap.add_argument("--manifest",required=True,help="CSV sample_id,smiles,ligand_sdf,complex_pdb,optional assay_type KD/KI")
 ap.add_argument("--esm-checkpoint",type=Path,required=True,help="Original local ESM2-650M weights, not bundled")
 ap.add_argument("--davis-ligands",type=Path,required=True,help="Original 68 DAVIS reference SMILES JSON, not bundled")
 ap.add_argument("--davis-model-2931",type=Path,required=True)
 ap.add_argument("--davis-model-2932",type=Path,required=True)
 ap.add_argument("--trained-residuals",type=Path,required=True,help="Source349-only fitted 4fold checkpoint dir")
 ap.add_argument("--out",type=Path,required=True,help="New label-free prediction CSV")
 ap.add_argument("--features-out",type=Path,help="Optional private source-only NPZ for 423/704 feature parity audit")
 ap.add_argument("--esm-device",choices=("auto","cpu","cuda"),default="auto")
 args=ap.parse_args()
 out=args.out.resolve()
 feat=args.features_out.resolve() if args.features_out else None
 if out.exists() or (feat and feat.exists()):raise FileExistsError("Refusing to overwrite raw inference output")
 inputs=read_inputs(args.manifest)
 entries=[]
 for n,row in enumerate(inputs,1):
  r=graph_from_raw(row["smiles"],row["ligand_sdf"],row["complex_pdb"],
   sequence=row["sequence"],receptor_chain=row["receptor_chain"])
  r["side"]=side_features(Chem.MolFromSmiles(row["smiles"]),r["sequence"],row["assay_type"])
  entries.append(r)
  print(f"RAW_NATIVE_QA_{n}/{len(inputs)} PASS",flush=True)
 prot=esm_mean([r["sequence"] for r in entries],args.esm_checkpoint,args.esm_device)
 ctx,raw,modelhash=backbone_context(
  [r["fingerprint"] for r in entries],
  [prot[r["sequence"]] for r in entries],
  [r["side"] for r in entries],
  args.davis_ligands,args.davis_model_2931,args.davis_model_2932)
 x2d=np.column_stack((ctx,raw))
 geom={k:np.stack([r["geometry"][k] for r in entries]).astype(np.float32) for k in ARMS}
 assert x2d.shape==(len(inputs),423)
 assert all(z.shape==(len(inputs),704) for z in geom.values())
 preds=load_source_fitted_3d(args.trained_residuals.resolve(),x2d,geom)
 preds["raw_davis_v5"]=raw.astype(float)
 if any(not np.isfinite(v).all() for v in preds.values()):
  raise ValueError("Prediction is nonfinite")
 out.parent.mkdir(parents=True,exist_ok=True)
 if feat:
  feat.parent.mkdir(parents=True,exist_ok=True)
  with feat.open("xb") as f:
   np.savez_compressed(f,ids=np.asarray([i["sample_id"] for i in inputs]),
    x2d=x2d.astype(np.float32),**geom)
 with out.open("x",encoding="utf8",newline="") as f:
  writer=csv.writer(f)
  writer.writerow(["sample_id","raw_davis_v5","calibrated_2d","real_3d","shuffled_3d","pocket_only"])
  for i,row in enumerate(inputs):
   writer.writerow([row["sample_id"]]+[repr(float(preds[k][i]))
    for k in ("raw_davis_v5","calibrated_2d","real_3d","shuffled_3d","pocket_only")])
 manifest={"status":"RAW_SMILES_SDF_PDB_TO_ORIGINAL_DYNAV5_REAL_SHUFFLED_POCKET_PREDICTIONS_PASS",
  "n_raw_complexes":len(inputs),"source_raw_manifest_SHA256":sha(args.manifest),
  "original_DAVIS2931_2932_sha256":modelhash,
  "source_trained_residual_run_SHA256":sha(args.trained_residuals.resolve()/"run.json"),
  "original_ESM2_650M_weights_SHA256":sha(args.esm_checkpoint),
  "prediction_csv_sha256":sha(out),
  "optional_label_free_features_sha256":sha(feat) if feat else None,
  "numeric_assay_labels_read":False}
 (out.with_suffix(".manifest.json")).write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
 print(json.dumps(manifest,indent=2),flush=True)
if __name__=="__main__":main()
