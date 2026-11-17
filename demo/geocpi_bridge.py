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
EXAMPLES = [
    {"sample_id": r["sample_id"], "smiles": r["smiles"], "sequence": r["sequence"],
     "source": "OpenBind 2026 experimental ligand-protein complex"}
    for r in rows[:6]
]

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
        if self.path == "/api/geocpi/health":
            return self.respond(200, {
                "status": "ok", "service": "geocpi-verified-native-bound",
                "available_bound_complexes": len(rows),
                "supported": "exact canonical SMILES + full receptor sequence",
                "is_pose_generation": False,
            })
        if self.path == "/api/geocpi/examples":
            return self.respond(200, {"examples": EXAMPLES})
        return self.respond(404, {"error": "Unknown route"})

    def do_POST(self):
        if self.path != "/api/geocpi/predict":
            return self.respond(404, {"error": "Unknown route"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 1 <= n <= 8192 or "application/json" not in self.headers.get("Content-Type", ""):
                raise ValueError("Expected a JSON request under 8 KB")
            body = json.loads(self.rfile.read(n))
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
    print(f"GeoFuse-CPI native-bound bridge: {len(rows)} qualified complexes; {len(by_pair)} unique SMILES/protein pairs", flush=True)
    print("http://127.0.0.1:8786/api/geocpi/health", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8786), Handler).serve_forever()
