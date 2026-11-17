"""Verify the shipped historical 3D aggregate results and updated V28 comparison.

Without --source-root: architecture and arithmetic only.
With --source-root: independently hash-check original *aggregate* source JSON.
No test-row Y is opened; 3D model test-label eligibility is unchanged.
"""
from pathlib import Path
import argparse,hashlib,json,math,sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"src"))
from dynacpi3d.model import check_architecture

ROOT=Path(__file__).resolve().parent
PRIMARY=ROOT/"results/biolip3_aggregates.json"
FULL=ROOT/"results/v28_full_davis_matched_perceiver.json"
PARITY=ROOT/"results/prepared_feature_exact_replay.json"
OPENBIND=ROOT/"results/openbind2026_single_target_482_aggregate.json"
V51=ROOT/"results/v51_scientific_audit_and_raw_reproducibility.json"
ORIGINAL_KEYS={
 "Dyna-real-3D":"original_DynaV5_plus_REAL_native_pair_geom",
 "Dyna-shuffled-3D":"original_DynaV5_plus_SHUFFLED_native_pair_geom",
 "Dyna-pocket-only":"original_DynaV5_plus_POCKET_only",
 "Dyna-calibrated-2D":"calibrated_original_DynaV5_2D",
 "PerceiverCPI-original":"original_unmodified_PerceiverCPI_4fold3ens"}
SOURCES=(
 "geometry_v6_20261115/v21_original_perceiver_HiQBind349_4fold_150ep3ens_external37_blind_20261116/V21_FIRST_SIX_ARM_MATCHED_PERCEIVER_REAL3D_SHUFFLE_POCKET_2D_BIOLIP3_37_NEW_EXPERIMENTAL_OUTCOME_ONCE.json",
 "geometry_v6_20261115/v22_BioLiP3_second_untouched_family_scaffold_cold_20261116/V22_SECOND36_PROSPECTIVE_EXPERIMENTAL_KIKD_SIXARM_FIRST_UNSEAL_MATCHED_RESULTS_ONCE.json")
MORE={
 "full_V28_source_training_manifest":"geometry_v6_20261115/v41_guarded_full_V28_original_Perceiver_12member_pipeline_20261116/V41_FULL_V28_PIPELINE_COMPLETION_WITH_SOURCE_SHA.json",
 "full_original_V28_label_free_prediction_manifest":"geometry_v6_20261115/v28_davis_matched_original_perceiver_pretraining_then_hiqbind349_20261116/V28_ORIGINAL_UNMODIFIED_DAVIS302_PRETRAINED_PAPERCPI_HIQ349_12MODEL_V21_37_V22_36_POSTHOC_NO_Y/V28_SOURCE_ORIGINAL_MATCHED_DAVIS_PAPERCPI_ALL12_CHECKPOINTS_NEW37_SECOND36_NOY_PREDICTION_SHA.json",
 "full_V28_first_score":"geometry_v6_20261115/v28_davis_matched_original_perceiver_pretraining_then_hiqbind349_20261116/V28_POSTHOC_DAVIS_SUPERVISED_MATCHED_ORIGINAL_Perceiver_4fold3ens_HIQ349_V21_V22_70_SCORES.json",
 "frozen_V42_plan":"geometry_v6_20261115/v41_guarded_full_V28_original_Perceiver_12member_pipeline_20261116/V42_FIXED_POSTHOC_FULL_V28_PEER_REVIEW_METRICS_ANALYSIS_PLAN_BEFORE_COMPLETE_NOY.json",
 "independent_V42_analysis":"geometry_v6_20261115/v41_guarded_full_V28_original_Perceiver_12member_pipeline_20261116/V42_FULL_DAVIS_PRETRAINED_12MEMBER_Perceiver_MSE_CINDEX_PEARSON_SPEARMAN_PAIREDCI_POSTHOC.json"}
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def close(a,b):return math.isclose(a,b,rel_tol=0,abs_tol=1e-10)
def main():
 ap=argparse.ArgumentParser(description="Verify actual 3D architecture, source-only aggregate research results")
 ap.add_argument("--source-root",type=Path,help="preserved local DynaCPI-3D-RnD clone; read-only SHA checks")
 args=ap.parse_args()
 a=json.loads(PRIMARY.read_text("utf8"));b=json.loads(FULL.read_text("utf8"))
 parity=json.loads(PARITY.read_text("utf8"))
 assert parity["status"]=="PASS_PREPARED_FEATURE_HISTORICAL_TRAIN349_SOURCE_ONLY_EXACT_REPLAY"
 assert parity["n_original_geometry_models_tensor_exact"]==12
 assert parity["n_external_label_free_predictions_exact"]==37
 assert parity["max_absolute_checkpoint_parameter_difference"]==0
 assert parity["max_absolute_external_NO_Y_prediction_difference"]==0
 audit=json.loads(V51.read_text("utf8"))
 assert audit["status"]=="V51_INDEPENDENT_SCIENTIFIC_AUDIT_AND_COMPLETE_RAW660_E2E_REPRODUCIBILITY_VERIFIED"
 assert audit["independent_six_arm_metric_entries_verified"]==54
 assert audit["independent_5000_scaffold_cluster_bootstrap_CI_bounds_verified"]==12
 assert audit["independent_ci_max_absolute_difference"]<1e-12
 assert audit["fresh_raw_source_bound_complexes_reprocessed"]==660
 assert audit["all_original_704D_REAL_SHUFFLED_POCKET_features_exact"]
 assert audit["all_original_166D_sequence_molecule_side_features_exact"]
 assert audit["max_final_five_arm_prediction_absolute_difference_pKd"]<.03
 assert audit["source_labeled_compounds_with_numeric_assay_from_only_non_qc_rows"]==4
 assert check_architecture()==47361
 external=json.loads(OPENBIND.read_text("utf8"))
 assert external["n_prelabel_selected"]==660 and external["n_labeled_accepted_compounds"]==482
 assert external["n_unique_Murcko_or_acyclic_scaffolds_labeled"]==264
 assert external["correct_native_distances_both_primary_MAE_CI_negative"] is False
 ex=external["scored_model_original_source_frozen"]
 assert ex["original_DynaV5_plus_REAL_native_pair_geom"]["RMSE"]>ex["raw_DAVIS_v5"]["RMSE"]
 assert ex["original_DynaV5_plus_REAL_native_pair_geom"]["RMSE"]>ex["original_full12_DAVISpretrained_Perceiver_ensemble"]["RMSE"]
 paired=external["four_fixed_paired_descriptive_scaffold_cluster_5000boot"]
 assert paired["REAL_minus_SHUFFLED"]["Cindex_delta_95pct_CI"][0]>0
 assert paired["REAL_minus_SHUFFLED"]["MAE_delta_95pct_CI"][0]<0<paired["REAL_minus_SHUFFLED"]["MAE_delta_95pct_CI"][1]
 assert a["n_per_cohort"]==[37,33]
 assert b["status"]=="V48_AGGREGATE_ONLY_SHA_VERIFIED_POSTHOC_FULL_DAVIS_PERCEIVER_FAIRNESS"
 assert (b["n_first"],b["n_second"],b["n_posthoc_pooled"])==(37,33,70)
 for oldname,newname in [
  ("Dyna-real-3D","DynaCPI-real-3D"),
  ("Dyna-shuffled-3D","DynaCPI-shuffled-3D"),
  ("Dyna-calibrated-2D","DynaCPI-calibrated-2D"),
  ("PerceiverCPI-original","PerceiverCPI-original-HiQ349")]:
  for label,key in (("V21_MSE","V21_37"),("V22_MSE","V22_33")):
   assert close(a["arms"][oldname][label],b["models"][newname][key]["MSE"])
 for name in b["models"]:
  model=b["models"][name]
  mse=(37*model["V21_37"]["MSE"]+33*model["V22_33"]["MSE"])/70
  assert close(mse,model["posthoc_pooled70"]["MSE"])
  assert close(math.sqrt(mse),model["posthoc_pooled70"]["RMSE"])
 r=b["models"]["DynaCPI-real-3D"]["posthoc_pooled70"]
 p=b["models"]["PerceiverCPI-original-DAVIS45-HiQ349"]["posthoc_pooled70"]
 saving=1-r["MSE"]/p["MSE"]
 assert close(saving,b["DynaCPI_real3D_MSE_reduction_vs_original_fully_DAVISpretrained_Perceiver_posthoc"])
 assert .49<saving<.51
 boot=b["contrasts_predeclared_before_V28_completion"]
 assert not boot["Dyna_REAL3D_minus_Dyna_SHUFFLED3D"]["Cindex_nominal_excludes0"]
 assert not boot["Dyna_REAL3D_minus_Dyna_SHUFFLED3D"]["MAE_nominal_excludes0"]
 print(f"PASS: model 47,361 params; original V21/V22 and full V28 arithmetic; {100*saving:.2f}% MSE improvement")
 if args.source_root:
  source=args.source_root
  paths=[source/x for x in SOURCES]
  for path in paths:
   if not path.is_file():raise FileNotFoundError(path)
  assert sha(paths[0])==a["provenance_original_V21_score_json_sha256"]
  assert sha(paths[1])==a["provenance_original_V22_score_json_sha256"]
  sa=json.loads(paths[0].read_text("utf8"))["six_arm_pooled_affinity_performance"]
  sb=json.loads(paths[1].read_text("utf8"))["six_arm_pooled_MSE_RMSE_MAE_R2"]
  for key,sourcekey in ORIGINAL_KEYS.items():
   assert close(sa[sourcekey]["MSE"],a["arms"][key]["V21_MSE"])
   assert close(sb[sourcekey]["MSE"],a["arms"][key]["V22_MSE"])
  for key,path in MORE.items():
   item=source/path
   if not item.is_file():raise FileNotFoundError(item)
   assert sha(item)==b["source_SHA256"][key],key
  v48=source/"geometry_v6_20261115/v48_final_fullDAVISpretrained_original_PerCI_fairness_publication_20261116"
  for fname,key in [
   ("V48_CLEAN_REPO_SOURCE_TRAIN349_TO_BLIND37_REPLAY_SOURCE_PREDICTION_PARITY.json","source_prediction_proof_audit_SHA256"),
   ("V48_12_RETRAINED_GEOMETRY_RESIDUAL_STATE_TENSOR_PARITY_NO_Y.json","source_checkpoint_proof_audit_SHA256")]:
   assert sha(v48/fname)==parity[key]
  v50=source/"geometry_v6_20261115/v50_OpenBind2026_single_target_new_Kd_native_strict_noY_20261117"
  assert sha(v50/"V50_FIRST_EXTERNAL_INDEPENDENT_OPENBIND2A_660_PREY_FIXED_KD_POSTFREEZE_6MODEL_SCORES.json")==sha(OPENBIND)
  for filename,expectedkey in [
   ("V50_FINAL_PKd_EXTERNAL_SCORING_PREREG_BEFORE_FIRST_Y.json","prelabel_score_protocol"),
   ("V50_PHASE3_FROZEN_PRE_Y_COMPOUND_POSE_SELECTION_NO_KD.json","prelabel_selection"),
   ("V50_OPENBIND660_ORIGINAL_DYNA5_FIVE_ARMS_FROZEN_BEFORE_KD_Y.npz","Dyna_five_arm_noY"),
   ("V50_OPENBIND660_ORIGINAL_UNMODIFIED_PERCEIVER_DAVIS_HIQ349_12PRED_NOY.npz","Original_Perceiver_twelve_noY")]:
   assert sha(v50/filename)==external["source_files_SHA256"][expectedkey]
  v51=source/"geometry_v6_20261115/v51_OpenBind_independent_scientific_audit_and_clean_raw_e2e_20261117"
  for fname,key in [
   ("V51_INDEPENDENT_OPENBIND482_FIRST_SCORE_EXACT_AUDIT_AND_5000_CLUSTER_REPLAY.json","independent_scientific_metric_and_bootstrap_audit"),
   ("V51_PINNED_RDKIT2025_CPU_RAW660_TO_FROZEN_V50_PARITY.json","independent_raw660_all5_model_parity_audit"),
   ("V51_SCIENTIFIC_SECOND_PASS_COMPOUND_DUPLICATE_ASSAY_QC_SENSITIVITY_NO_MODEL_TUNING.json","independent_source_molecular_uniqueness_and_QC_audit"),
   ("V51_POSTHOC_EXCLUDE_FOUR_QC_ROW_ONLY_KD_GROUPS_478_SENSITIVITY.json","posthoc_strict_rowQC_478_sensitivity")]:
   assert sha(v51/fname)==audit["source_proof_SHA256"][key],fname
  assert sha(ROOT/"src/dynacpi3d/geometry.py")=="465aeb2cb971ba332a75d7e622a2d1d84bf0947aa827278730020e659792e727"
  print("PASS: 2 BioLiP3 SHA + 5 V28/V41/V42 SHA + V48 model replay + V50 external freeze + V51 independent 54 metric, 12 CI, 660 raw-source parity checks")
 else:
  print("NOTE: for original source hash audit use --source-root ../DynaCPI-3D-RnD")
 print("Privacy: checked aggregate reports only; no protected assay Y opened.")

if __name__=="__main__":main()
