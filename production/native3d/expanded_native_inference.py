"""Label-free expanded native-structure inference lookup.

Reads precomputed frozen-v48 predictions only. Does not load affinity labels,
retrain the model, generate poses, or treat IC50/EC50 as Ki/Kd.
"""
from __future__ import annotations
import csv
import json
import statistics
import hashlib
from pathlib import Path
import numpy as np


class ExpandedNativeInference:
    def __init__(self, catalog, log_dir: Path):
        self.catalog = catalog
        self.log_dir = Path(log_dir)
        inputs = self.log_dir / "NATIVE_CATALOG_10224_2D_INPUTS_NOY.npz"
        predictions = self.log_dir / "NATIVE_CATALOG_10224_FROZEN_V48_PREDICTIONS_NOY.csv"
        if not inputs.is_file() or not predictions.is_file():
            raise FileNotFoundError("Expanded label-free feature/prediction archives are missing")
        with np.load(inputs, allow_pickle=False) as z:
            ids = [str(x) for x in z["ids"].tolist()]
            endpoints = z["endpoint"].astype(str)
            external = z["external_candidate"].astype(bool)
            train_overlap = z["training_overlap_union"].astype(bool)
            openbind = z["openbind_consumed"].astype(bool)
            construct = z["assay_construct_verified"].astype(bool)
            sequence_match = z["sequence_match"].astype(str)
        catalog_ids = [str(x["record_id"]) for x in catalog.public]
        if ids != catalog_ids or len(ids) != 10224:
            raise RuntimeError("Expanded inference metadata is not aligned with the native catalog")
        self.meta = {
            rid: {
                "endpoint": str(endpoints[i]),
                "external_candidate": bool(external[i]),
                "training_overlap": bool(train_overlap[i]),
                "openbind_consumed": bool(openbind[i]),
                "assay_construct_verified": bool(construct[i]),
                "sequence_match": str(sequence_match[i]),
            }
            for i, rid in enumerate(ids)
        }
        self.predictions = {}
        with predictions.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rid = row["record_id"]
                scenario = row["assay_scenario"]
                if rid not in self.meta or not self.meta[rid]["external_candidate"]:
                    raise RuntimeError(f"Prediction row is not an eligible external record: {rid}")
                self.predictions[(rid, scenario)] = {
                    "record_id": rid,
                    "source": row["source"],
                    "structure_id": row["structure_id"],
                    "assay_endpoint": row["assay_endpoint"],
                    "assay_scenario": scenario,
                    "scenario_basis": row["scenario_basis"],
                    "pred_2d": float(row["pred_2d"]),
                    "pred_real": float(row["pred_real"]),
                    "pred_shuffled": float(row["pred_shuffled"]),
                    "pred_pocket": float(row["pred_pocket"]),
                    "real_minus_2d": float(row["real_minus_2d"]),
                    "real_minus_shuffled": float(row["real_minus_shuffled"]),
                    "fold_sd_real": float(row["fold_sd_real"]),
                    "sequence_match": row["sequence_match"],
                    "assay_construct_verified": row["assay_construct_verified"].lower() == "true",
                }
        if len(self.predictions) != 6744:
            raise RuntimeError(f"Unexpected expanded prediction count: {len(self.predictions)}")
        # Deterministic, label-free examples for the research UI. Only known KD/KI
        # metadata is offered by default; these are not accuracy validations.
        self.examples = []
        example_pairs = set()
        for source_name in ("HIQBIND_NEW_PILOT_NATIVE", "HIQBIND_NEW_BULK_NATIVE",
                            "HIQBIND_RETRIEVAL_SCALEUP_NATIVE", "HIQBIND_RETRIEVAL_ALTERNATE_POSE_NATIVE"):
            for assay in ("KD", "KI"):
                added = 0
                for record in catalog.public:
                    rid = str(record["record_id"])
                    meta = self.meta[rid]
                    key = (record["smiles"], record["sequence"])
                    if record["source_record"] != source_name or not meta["external_candidate"] or meta["endpoint"] != assay:
                        continue
                    if (rid, assay) not in self.predictions or key in example_pairs:
                        continue
                    example_pairs.add(key)
                    self.examples.append({
                        "record_id": rid, "structure_id": record["structure_id"],
                        "smiles": record["smiles"], "sequence": record["sequence"],
                        "compound_name": record["compound_name"], "protein_name": record["protein_name"],
                        "assay_type": assay, "source": record["source"], "source_url": record["source_url"],
                        "assay_construct_verified": False,
                    })
                    added += 1
                    if added == 1:
                        break
        self.status = {
            "status": "ready",
            "catalog_records": len(ids),
            "external_nonoverlap_records": int(external.sum()),
            "known_KD_KI_records": int(np.sum(external & np.isin(endpoints, ["KD", "KI"]))),
            "unknown_endpoint_records": int(np.sum(external & (endpoints == "UNKNOWN"))),
            "IC50_EC50_not_scored": int(np.sum(external & np.isin(endpoints, ["IC50", "EC50"]))),
            "precomputed_prediction_rows": len(self.predictions),
            "assay_construct_verified_external_records": int(construct[external].sum()),
            "no_affinity_labels_loaded": True,
        }

    @staticmethod
    def _median(rows, key):
        return float(statistics.median(float(r[key]) for r in rows))

    def predict(self, pair_key, assay_type=None):
        if assay_type is not None:
            assay_type = str(assay_type).upper()
            if assay_type not in ("KD", "KI"):
                return 400, {"status": "invalid_assay_type", "error": "assay_type must be KD or KI"}
        if isinstance(pair_key, tuple) and len(pair_key) == 2:
            pair_key = hashlib.sha256((str(pair_key[0]) + "|" + str(pair_key[1])).encode()).hexdigest()
        hits = self.catalog.bycanonical.get(pair_key, [])
        if not hits:
            return 422, {
                "status": "no_verified_native_pose",
                "error": "No exact canonical-SMILES and observed receptor-sequence match exists in the expanded native catalog.",
                "geometry_used": False,
            }
        grouped = {}
        excluded = {"training_overlap": 0, "openbind_consumed": 0, "IC50_EC50_unsupported": 0, "unknown_endpoint_assay_type_required": 0}
        for i in hits:
            record = self.catalog.public[i]
            rid = str(record["record_id"])
            meta = self.meta[rid]
            if meta["openbind_consumed"]:
                excluded["openbind_consumed"] += 1
                continue
            if meta["training_overlap"]:
                excluded["training_overlap"] += 1
                continue
            ep = meta["endpoint"]
            if ep in ("IC50", "EC50"):
                excluded["IC50_EC50_unsupported"] += 1
                continue
            if ep in ("KD", "KI"):
                scenario, basis = ep, "source_metadata"
            elif ep == "UNKNOWN":
                if assay_type is None:
                    excluded["unknown_endpoint_assay_type_required"] += 1
                    continue
                scenario, basis = assay_type, "user_assumption"
            else:
                excluded["unknown_endpoint_assay_type_required"] += 1
                continue
            row = self.predictions.get((rid, scenario))
            if row is None:
                continue
            key = (scenario, basis)
            grouped.setdefault(key, []).append(row)
        if not grouped:
            if excluded["unknown_endpoint_assay_type_required"]:
                return 422, {
                    "status": "assay_type_required",
                    "error": "The matched structure has no verified KD/KI endpoint. Supply assay_type='KD' or 'KI' for a clearly marked hypothetical scenario.",
                    "excluded": excluded,
                    "geometry_used": False,
                }
            if excluded["IC50_EC50_unsupported"]:
                return 422, {
                    "status": "unsupported_assay_endpoint",
                    "error": "The frozen model supports KD/KI inputs only. IC50/EC50 cannot be converted without assay-specific conditions.",
                    "excluded": excluded,
                    "geometry_used": False,
                }
            if excluded["training_overlap"]:
                return 422, {
                    "status": "training_overlap_excluded",
                    "error": "This exact pair or PDB overlaps the original 349-pair training set and is excluded from expanded external inference.",
                    "excluded": excluded,
                    "geometry_used": False,
                }
            if excluded["openbind_consumed"]:
                return 422, {
                    "status": "evaluation_already_unsealed",
                    "error": "This pair belongs to the previously unsealed OpenBind evaluation set; use the existing verified prediction route.",
                    "excluded": excluded,
                    "geometry_used": False,
                }
            return 422, {"status": "no_expanded_prediction", "excluded": excluded, "geometry_used": False}
        results = []
        structures = []
        for (scenario, basis), rs in sorted(grouped.items()):
            score_label = "pKd" if scenario == "KD" else "pKi"
            native = [float(r["pred_real"]) for r in rs]
            results.append({
                "assay_type": scenario,
                "score_label": score_label,
                "basis": basis,
                "pose_count": len(rs),
                "median_2d_baseline": self._median(rs, "pred_2d"),
                "median_native_3d_prediction": self._median(rs, "pred_real"),
                "native_3d_min": float(min(native)),
                "native_3d_max": float(max(native)),
                "native_3d_range": float(max(native) - min(native)),
                "median_shuffled_control": self._median(rs, "pred_shuffled"),
                "median_pocket_control": self._median(rs, "pred_pocket"),
                "median_3d_minus_2d": self._median(rs, "real_minus_2d"),
                "median_3d_minus_shuffled": self._median(rs, "real_minus_shuffled"),
                "median_fourfold_spread": self._median(rs, "fold_sd_real"),
            })
            structures.extend(rs)
        return 200, {
            "status": "exploratory",
            "model": "GeoFuse-CPI frozen v48 fourfold; no retraining",
            "match_basis": "exact canonical SMILES + exact observed receptor sequence",
            "matched_structure_records": len(hits),
            "scored_structure_records": len(structures),
            "assay_results": results,
            "structures": structures,
            "excluded": excluded,
            "geometry_used": True,
            "geometry_source": "deposited native-bound coordinates / native pocket graphs",
            "backbone_input_dim": 423,
            "geometry_input_dim": 704,
            "assay_construct_verified": False,
            "no_affinity_labels_loaded": True,
            "notice": "Exploratory frozen-model inference, not independent accuracy validation. Assay construct identity is not verified for these external structures. UNKNOWN endpoints use an explicit user-selected KD/KI scenario; IC50/EC50 are not scored. Multiple native structures are reported separately and summarized by median/range.",
        }
