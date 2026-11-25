"""GeoFuse-CPI real-native-geometry bridge for exact compound/protein matches.

Never substitutes an RDKit visual conformer or guessed pose for an experimental
bound ligand-protein structure. Matches source metadata (no assay labels) and
runs the original frozen fourfold GeoFuse native 3D checkpoint on 423/704 features.
"""
from __future__ import annotations
import csv
import json
import os
import sys
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DYNACPI_3D_PAPER", str(HERE.parent))).resolve()
MANIFEST = ROOT / "private" / "v51_raw660_structures" / "raw660.csv"
FEATURES = ROOT / "private" / "v51_raw660_RDKIT2025_features_noY.npz"
assert MANIFEST.is_file() and FEATURES.is_file(), "Original 660 label-free experimental-bound inputs are required"
os.environ["DYNACPI_3D_PAPER"] = str(ROOT)
sys.path.insert(0, str(HERE))
from backend import Model  # source-trained, unmodified frozen native 3D checkpoint

def canonical(smiles: str) -> str:
    if not isinstance(smiles, str) or not 1 <= len(smiles) <= 500:
        raise ValueError("SMILES must contain 1–500 characters")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("Invalid compound SMILES")
    return Chem.MolToSmiles(mol, isomericSmiles=True)

def normalize_sequence(sequence: str) -> str:
    if not isinstance(sequence, str):
        raise ValueError("Protein sequence is required")
    seq = "".join(line.strip() for line in sequence.splitlines() if not line.startswith(">")).upper()
    if not 1 <= len(seq) <= 2048 or any(x not in "ACDEFGHIKLMNPQRSTVWYX" for x in seq):
        raise ValueError("Invalid protein sequence")
    return seq

with FEATURES.open("rb") as f:
    with np.load(f, allow_pickle=False) as z:
        arrays = {key: z[key].copy() for key in ("x2d", "real", "shuffled", "pocket")}
        ids = [str(x) for x in z["ids"].tolist()]
rows = list(csv.DictReader(MANIFEST.open(encoding="utf8", newline="")))
if len(ids) != 660 or len(rows) != 660 or ids != [r["sample_id"] for r in rows]:
    raise RuntimeError("Raw structure manifest does not match frozen label-free geometry features")
by_pair = defaultdict(list)
for i, r in enumerate(rows):
    by_pair[(canonical(r["smiles"]), normalize_sequence(r["sequence"]))].append(i)

ENGINE = Model()
SOURCE_LINK = "https://zenodo.org/records/20026661"
PROTEIN_NAME = "Coxsackievirus A16 (CVA16) 2A protease"
def identity(r):
    mol = Chem.MolFromSmiles(r["smiles"])
    return {"sample_id": r["sample_id"], "smiles": r["smiles"], "sequence": r["sequence"],
            "compound_name": "Research compound " + r["sample_id"],
            "compound_formula": rdMolDescriptors.CalcMolFormula(mol),
            "protein_name": PROTEIN_NAME,
            "source_url": SOURCE_LINK,
            "source": "OpenBind experimental native-bound structure (CVA16 surrogate for EV-A71)"}

CATALOG = [identity(r) for r in rows]
EXAMPLES = [
    identity(r) for r in rows[:6]
]
# Two distinct compounds with one exact full receptor sequence: real, label-free input pairs.
# This lets the comparison UI demonstrate two genuine supported model calls.
compare_by_target = defaultdict(dict)
for r in rows:
    key = normalize_sequence(r["sequence"])
    compare_by_target[key].setdefault(canonical(r["smiles"]), r)
COMPARE_EXAMPLES = []
for target, ligands in sorted(compare_by_target.items(), key=lambda item: -len(item[1])):
    if len(ligands) < 2:
        continue
    first, second = list(ligands.values())[:2]
    COMPARE_EXAMPLES.append({
        "sequence": target,
        "compound_a": identity(first),
        "compound_b": identity(second),
        "protein_name": PROTEIN_NAME,
        "source": "OpenBind 2026 native-bound structures, two distinct ligands, same receptor",
    })
    if len(COMPARE_EXAMPLES) == 5:
        break

from native_catalog import NativeCatalog, PREFIX as STRUCTURE_PREFIX
try:
    NATIVE_CATALOG = NativeCatalog(by_pair, ids)
except Exception as exc:
    print("Native retrieval catalog unavailable:", type(exc).__name__, flush=True)
    NATIVE_CATALOG = NativeCatalog(by_pair, ids, root=HERE / "not-installed")

from expanded_native_inference import ExpandedNativeInference
try:
    EXPANDED_INFERENCE = ExpandedNativeInference(NATIVE_CATALOG, HERE / "local_v151_service_logs" / "v358_corrected_20261125")
except Exception as exc:
    print("Expanded native inference unavailable:", type(exc).__name__, str(exc), flush=True)
    EXPANDED_INFERENCE = None

class Handler(BaseHTTPRequestHandler):
    def respond(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith(STRUCTURE_PREFIX + "/"):
            return NATIVE_CATALOG.handle(self)
        if self.path == "/api/geocpi/health":
            return self.respond(200, {
                "status": "ok", "service": "geocpi-verified-native-bound",
                "available_bound_complexes": len(rows),
                "native_retrieval_catalog": NATIVE_CATALOG.status(),
                "expanded_inference": EXPANDED_INFERENCE.status if EXPANDED_INFERENCE else {"status": "unavailable"},
                "supported": "exact canonical SMILES + full receptor sequence; expanded research route is separate",
                "is_pose_generation": False,
            })
        if self.path == "/api/geocpi/expanded-inference/status":
            return self.respond(200 if EXPANDED_INFERENCE else 503,
                EXPANDED_INFERENCE.status if EXPANDED_INFERENCE else {"status": "unavailable"})
        if self.path == "/api/geocpi/expanded-inference/examples":
            return self.respond(200 if EXPANDED_INFERENCE else 503,
                {"examples": EXPANDED_INFERENCE.examples, "exploratory_only": True,
                 "no_affinity_labels_loaded": True} if EXPANDED_INFERENCE else {"status": "unavailable"})
        if self.path in ("/api/geocpi/cold-summary", "/api/geocpi/cold/DAVIS", "/api/geocpi/cold/KIBA", "/api/geocpi/cold/METZ"):
            try:
                from cold_comparison import load_cold, cold_summary
                return self.respond(200, {"datasets":cold_summary()} if self.path.endswith("cold-summary") else load_cold(self.path.rsplit("/",1)[-1]))
            except Exception:
                import traceback
                traceback.print_exc()
                return self.respond(503, {"error":"Verified cold-compound archive unavailable."})
        if self.path == "/api/geocpi/head-to-head":
            try:
                from head_to_head import load_head_to_head
                payload = load_head_to_head()
                assert set(r["sample_id"] for r in payload["rows"] + payload["unmeasured"]) == set(ids)
                return self.respond(200, payload)
            except Exception:
                import traceback
                traceback.print_exc()
                return self.respond(503, {"error": "Verified matched OpenBind archive unavailable."})
        if self.path == "/api/geocpi/examples":
            return self.respond(200, {"examples": EXAMPLES})
        if self.path == "/api/geocpi/catalog":
            return self.respond(200, {"examples": CATALOG})
        if self.path == "/api/geocpi/compare-examples":
            return self.respond(200, {"examples": COMPARE_EXAMPLES})
        return self.respond(404, {"error": "Unknown route"})

    def do_POST(self):
        if self.path not in ("/api/geocpi/predict", "/api/geocpi/predict-expanded"):
            return self.respond(404, {"error": "Unknown route"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 1 <= n <= 8192 or "application/json" not in self.headers.get("Content-Type", ""):
                raise ValueError("Expected a JSON request under 8 KB")
            body = json.loads(self.rfile.read(n))
            if self.path == "/api/geocpi/predict-expanded":
                if EXPANDED_INFERENCE is None:
                    return self.respond(503, {"status": "expanded_inference_unavailable"})
                if not isinstance(body, dict) or not {"smiles", "sequence"}.issubset(body) or set(body) - {"smiles", "sequence", "assay_type"}:
                    raise ValueError("Provide smiles, sequence, and optional assay_type")
                key = (canonical(body["smiles"]), normalize_sequence(body["sequence"]))
                code, payload = EXPANDED_INFERENCE.predict(key, body.get("assay_type"))
                return self.respond(code, payload)
            if not isinstance(body, dict) or set(body) != {"smiles", "sequence"}:
                raise ValueError("Provide exactly smiles and sequence")
            key = (canonical(body["smiles"]), normalize_sequence(body["sequence"]))
            matches = by_pair.get(key)
            if not matches:
                return self.respond(422, {
                    "status": "no_verified_native_pose",
                    "error": "No experimentally bound complex matches this exact SMILES and full protein sequence in the local 660-structure set. 3D prediction was not run.",
                    "geometry_used": False,
                })
            i = matches[0]
            entry = {name: arr[i:i+1] for name, arr in arrays.items()}
            predictions = ENGINE.predict(entry, ("2d", "real"))
            score = float(predictions["real"][0])
            base = float(predictions["2d"][0])
            return self.respond(200, {
                "status": "ok", "model": "GeoFuse-CPI frozen native-bound fourfold",
                "prediction_pKd": round(score, 6),
                "calibrated_2d_pKd": round(base, 6),
                "sample_id": ids[i],
                "matched_complexes": len(matches),
                "geometry_used": True,
                "geometry_source": "OpenBind 2026 experimental native-bound ligand-protein crystal structure",
                "geometry_input_dim": 704,
                "backbone_input_dim": 423,
                "notice": "Exact compound+protein source match. Uses experimentally bound 3D geometry, not a generated docking pose. OpenBind evaluation labels have been previously unsealed; this is an exploratory research demonstration, not independent validation.",
            })
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            return self.respond(400, {"error": str(error)})
        except Exception:
            import traceback
            traceback.print_exc()
            return self.respond(500, {"error": "Frozen 3D inference failed. Inspect local server output."})

    def log_message(self, fmt, *args):
        print("[GeoCPI native 3D] " + fmt % args, flush=True)

if __name__ == "__main__":
    port = int(os.environ.get("GEOFUSE_BRIDGE_PORT", "8786"))
    print(f"GeoFuse-CPI native-bound bridge: {len(rows)} qualified complexes; {len(by_pair)} unique SMILES/protein pairs", flush=True)
    print(f"http://127.0.0.1:{port}/api/geocpi/health", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
