"""Export the historical TRAIN349 feature contract from the preserved research clone.

Creates ONLY local private feature arrays, using exactly the original 349
TRAIN labels. Never accesses HiQBind 75 DEV/TEST or future BioLiP3 Ki/Kd
values. The 37 BioLiP3 input features are frozen LABEL-FREE.
Do not commit the private/ output directory.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np

V17="geometry_v6_20261115/v17_frozen_original_DynaV5_native_pair_704D_HiQBind_TRAIN349_20261116"
V20="geometry_v6_20261115/v20_new_BioLiP3_37_native_external_labelblind_model_inputs_20261116"
ROLE="geometry_v6_20261115/hiqbind_v9_trainonly_alignment30_4fold_strict_ablation_20261116/TRAIN_349_LOCAL30_FOUR_FOLD_LABELBLIND_ROLES.npz"
LABEL="geometry_v6_20261115/hiqbind_v9_fresh_structural_source_20261116/V9_TRAIN_DEV_ONLY_SOURCE_AFFINITIES_TEST_Y_NEVER_EXTRACTED.npz"
SOURCE=V17+"/V17_ORIGINAL_DAVIS_V5_423D_AND_BOUND349_REAL_SHUFFLE_POCKET_704D_NO_Y.npz"
BLIND=V20+"/V20_NEW_BIOLIP3_37_NATIVE_REAL_SHUFFLED_POCKET_704D_AND_ORIGINAL_DYNAV5_423D_NO_AFFINITY.npz"
LOCK=V17+"/V17_PRE_FIT_ALL_CODE_REAL_V5_CONTEXT_PROTEIN_FOLDS_AND_LABEL_TRAIN_SHA_LOCK.json"

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description="Prepare private TRAIN-only historical source feature input")
    p.add_argument("--source-root",type=Path,required=True,help="existing DynaCPI-3D-RnD folder")
    p.add_argument("--out",type=Path,default=Path("private"))
    a=p.parse_args()
    root=a.source_root.resolve();out=a.out.resolve()
    if out.exists():raise FileExistsError("Refuse to overwrite private source arrays: "+str(out))
    files={name:root/path for name,path in
        [("FEATURE",SOURCE),("ROLE",ROLE),("LABEL",LABEL),("BLIND",BLIND),("LOCK",LOCK)]}
    for v in files.values():
        if not v.is_file():raise FileNotFoundError(str(v))
    locked=json.loads(files["LOCK"].read_text(encoding="utf8"))
    for label,expected in [
       ("verified_frozen_original_v5_plus_native_geometry_input_SHA256","FEATURE"),
       ("frozen_protein_local30_fourfold_roles_SHA256","ROLE"),
       ("original_train_only_HiQBind_y_input_sha256","LABEL")]:
        if sha(files[expected])!=locked[label]:raise ValueError("Historical before-fit source hash mismatch: "+label)
    with np.load(files["FEATURE"],allow_pickle=False) as z:
        orig=z["source_TRAIN_original_ordinal"].astype(int)
        pdb=z["source_TRAIN_PDB_id"].astype(str)
        x2d=np.column_stack([
             z["frozen_original_DAVIS_trained_DynaV5_2D_tower_context422"].astype(np.float32),
             z["frozen_original_DAVIS_trained_DynaV5_prior_prediction"].astype(np.float32)])
        geo={k:z[k].astype(np.float32) for k in ("real","shuffled","pocket")}
    with np.load(files["ROLE"],allow_pickle=False) as z:
        if not np.array_equal(orig,z["original_TRAIN_source_ordinal"]):
            raise ValueError("Source ordinal mismatch")
        if not np.array_equal(pdb,z["original_TRAIN_PDB"].astype(str)):
            raise ValueError("Source PDB mismatch")
        groups=z["protein_group_id"].astype(int)
        splits={k:z[k].astype(int) for k in
            [f"{kind}_{i}" for i in range(4) for kind in ("fit","dev")]}
    # npz fields are fetched LAZILY. The nearby 75 protected DEV Y values
    # are explicitly NEVER dereferenced.
    with np.load(files["LABEL"],allow_pickle=False) as z:
        if not np.array_equal(orig,z["source_ordinal_TRAIN"].astype(int)):
            raise ValueError("Old349 original TRAIN label ID mismatch")
        y=z["p_affinity_TRAIN"].astype(np.float64)
    if x2d.shape!=(349,423) or any(v.shape!=(349,704) for v in geo.values()) or len(y)!=349:
        raise ValueError("Historical original exact shapes changed")
    with np.load(files["BLIND"],allow_pickle=False) as z:
        ids=z["PDB_ID"].astype(str)
        held=np.column_stack([
           z["original_DAVIS_trained_DynaV5_422D_context"].astype(np.float32),
           z["original_DAVIS_trained_DynaV5_RAW_prediction"].astype(np.float32)])
        ext={k:z[k].astype(np.float32) for k in ("real","shuffled","pocket")}
    if len(ids)!=37 or held.shape!=(37,423) or any(v.shape!=(37,704) for v in ext.values()):
        raise ValueError("Frozen source-only external 37 feature sizes changed")
    out.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(out/"train349.npz",x2d=x2d,groups=groups,y=y,**geo)
    np.savez_compressed(out/"folds349.npz",**splits)
    np.savez_compressed(out/"external37_NO_Y.npz",x2d=held,ids=ids,**ext)
    report={
      "status":"LOCAL_ONLY_HIQ349_TRAIN_AND_BIOLIP3_37_NOY_EXPORTED",
      "source_file_sha256":{key:sha(files[key]) for key in ("FEATURE","ROLE","LABEL","BLIND")},
      "source_train_rows":349,"external_frozen_source_rows":37,
      "only_label_field_dereferenced":"p_affinity_TRAIN",
      "historical_HiQ75_DEV_TEST_and_BioLiP3_external_Y_untouched":True,
      "note":"Never commit private data; historical full experimental numbers already separately scored in original source."
    }
    (out/"manifest.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print("Wrote private TRAIN349 features, original group-fold roles, and label-free external37 inputs:",out)

if __name__=="__main__":
    main()
