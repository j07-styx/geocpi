"""Local, label-free HTTP inference for the *actual* frozen DynaCPI-3D v48 ensemble.

The model expects prepared features, not raw SMILES, protein sequences or PDBs.
Original DynaCPI-Backend and DynaCPI-3D-Paper are read-only from this service.
Only start on 127.0.0.1; trusted joblib checkpoints must remain local.
"""
from __future__ import annotations

import io
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import joblib
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
PAPER = Path(os.environ.get("DYNACPI_3D_PAPER", str(next(
    (p for p in (HERE.parent / "GeoFuse-3D", HERE.parent / "DynaCPI-3D-Paper") if p.is_dir()),
    HERE.parent / "GeoFuse-3D",
))))
RUN = PAPER / "runs" / "v48_train349_source_fourfold_replay"
EXAMPLE = PAPER / "private" / "external37_NO_Y.npz"
sys.path.insert(0, str(PAPER / "src"))
from dynacpi3d import ExplicitPairResidual

MODES = ("2d", "real", "shuffled", "pocket")
BLOCKED_LABELS = {"y", "label", "labels", "target", "targets", "affinity", "pkd", "pki"}
MAX_ROWS = 256
MAX_BYTES = 12 * 1024 * 1024
torch.set_num_threads(2)


class InputError(ValueError):
    pass


def validate_arrays(arrays, requested_modes):
    if set(arrays) & BLOCKED_LABELS:
        raise InputError("Inference must be label-free (y/label/affinity fields are forbidden).")
    if "x2d" not in arrays:
        raise InputError("Missing x2d (N,423).")
    x = np.asarray(arrays["x2d"], dtype=np.float32)
    if x.ndim != 2 or not (1 <= x.shape[0] <= MAX_ROWS) or x.shape[1] != 423:
        raise InputError("x2d must have shape (N,423), with 1-256 examples.")
    if not np.isfinite(x).all():
        raise InputError("x2d contains NaN/Inf.")
    features = {"x2d": x}
    for mode in requested_modes:
        if mode == "2d":
            continue
        if mode not in arrays:
            raise InputError(f"Missing {mode} geometry feature matrix (N,704).")
        v = np.asarray(arrays[mode], dtype=np.float64)
        if v.shape != (x.shape[0], 704) or not np.isfinite(v).all():
            raise InputError(f"{mode} must have shape (N,704) with all finite values.")
        features[mode] = v
    if "ids" in arrays:
        ids = np.asarray(arrays["ids"])
        if ids.ndim != 1 or len(ids) != len(x) or ids.dtype.kind not in ("U", "S", "i", "u"):
            raise InputError("ids must be a 1D string/integer array aligned with examples.")
        ids = [str(i) for i in ids.tolist()]
    else:
        ids = [str(i + 1) for i in range(len(x))]
    if len(set(ids)) != len(ids) or any(len(s) > 120 for s in ids):
        raise InputError("Example IDs must be unique and at most 120 characters.")
    return features, ids


def parse_modes(mode):
    if mode == "all":
        return MODES
    if mode not in MODES:
        raise InputError("mode must be one of: all, 2d, real, shuffled, pocket")
    return (mode,)


def npz_dict(blob):
    try:
        with np.load(io.BytesIO(blob), allow_pickle=False) as z:
            if set(z.files) & BLOCKED_LABELS:
                raise InputError("Inference file contains outcome labels; provide a label-free NPZ.")
            permitted = {"x2d", "real", "shuffled", "pocket", "ids"}
            if set(z.files) - permitted:
                raise InputError("Unexpected NPZ keys; use x2d, real, shuffled, pocket, ids.")
            return {k: z[k].copy() for k in z.files}
    except (OSError, EOFError, ValueError, KeyError) as err:
        if isinstance(err, InputError):
            raise
        raise InputError("Invalid NPZ archive or unsafe array type.") from err


class Model:
    def __init__(self):
        self.manifest = json.loads((RUN / "run.json").read_text(encoding="utf-8"))
        if self.manifest.get("status") != "SOURCE_TRAIN_ONLY_COMPLETE_NOT_EXTERNAL_TEST":
            raise RuntimeError("Unrecognized frozen 3D checkpoint.")
        self.folds = int(self.manifest["folds"])
        if self.folds != 4:
            raise RuntimeError("Expected four source-trained folds.")
        self.lock = threading.RLock()
        self.calibrators = []
        self.geometry = {}
        for fold in range(self.folds):
            models = joblib.load(RUN / f"fold_{fold}" / "calibrators.joblib")
            if len(models) != 3:
                raise RuntimeError("Expected three 2D calibrators per fold.")
            self.calibrators.append(models)

    def _head(self, fold, mode):
        key = (fold, mode)
        if key not in self.geometry:
            root = RUN / f"fold_{fold}"
            with np.load(root / f"{mode}_norm.npz", allow_pickle=False) as z:
                mu = z["mean"].copy()
                std = z["std"].copy()
                scale = float(z["scale"])
            if mu.shape != (704,) or std.shape != (704,) or np.any(std <= 0):
                raise RuntimeError("Bad frozen feature normalization.")
            model = ExplicitPairResidual()
            model.load_state_dict(torch.load(root / f"{mode}.pt", map_location="cpu", weights_only=True))
            model.eval()
            self.geometry[key] = (mu, std, scale, model)
        return self.geometry[key]

    def predict(self, arrays, modes):
        with self.lock, torch.inference_mode():
            x = arrays["x2d"]
            fold_values = {mode: [] for mode in modes}
            for fold in range(self.folds):
                base = np.mean([m.predict(x) for m in self.calibrators[fold]], axis=0)
                for mode in modes:
                    if mode == "2d":
                        fold_values[mode].append(base)
                        continue
                    mu, std, scale, head = self._head(fold, mode)
                    vec = ((arrays[mode] - mu) / std).astype(np.float32)
                    residual = head(torch.from_numpy(vec)).numpy().astype(float)
                    fold_values[mode].append(base + scale * residual)
            result = {mode: np.mean(fold_values[mode], axis=0) for mode in modes}
            if any(not np.isfinite(v).all() for v in result.values()):
                raise RuntimeError("Non-finite inference output.")
            return result


ENGINE = Model()


def response_payload(arrays, ids, modes, input_source):
    features, ids = validate_arrays(arrays, modes)
    scores = ENGINE.predict(features, modes)
    entries = []
    for i, sid in enumerate(ids):
        row = {"sample_id": sid, "scores": {m: round(float(scores[m][i]), 6) for m in modes}}
        if "real" in modes and "2d" in modes:
            row["real_minus_2d"] = round(float(scores["real"][i] - scores["2d"][i]), 6)
        if "real" in modes and "shuffled" in modes:
            row["real_minus_shuffled"] = round(float(scores["real"][i] - scores["shuffled"][i]), 6)
        entries.append(row)
    return {
        "status": "ok", "model": "DynaCPI-3D v48 frozen source-TRAIN349 fourfold ensemble",
        "n_samples": len(ids), "modes": list(modes), "input_source": input_source,
        "unit": "source-specific affinity log scale (pKi/pKd)",
        "predictions": entries,
        "notice": "Predictions use pretrained 2D features and experimentally observed native-bound geometry. Model score deltas are not proof of improved accuracy or confidence intervals.",
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def send(self, status, data):
        blob = json.dumps(data, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(blob)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/v3/health":
            return self.send(200, {
                "status": "ok", "service": "dynacpi-3d-native-bound",
                "model_version": "v48-train349-fourfold", "folds": ENGINE.folds,
                "feature_dimensions": {"x2d": 423, "native_3d": 704},
                "demo_available": EXAMPLE.is_file(), "accepts_raw_smiles_or_pdb": False,
                "checkpoint": str(RUN),
            })
        if path == "/api/v3/examples":
            if not EXAMPLE.is_file():
                return self.send(503, {"error": "Local label-free example features unavailable."})
            with np.load(EXAMPLE, allow_pickle=False) as z:
                ids = [str(s) for s in z["ids"].tolist()]
            return self.send(200, {"examples": ids, "source": "37 label-free BioLiP3 prepared native-bound complexes", "no_outcome_labels": True})
        if path == "/api/v3/metadata":
            return self.send(200, {
                "model": "Frozen DynaCPI v5 + bounded native 3D residual",
                "architecture": "423D 2D features + 704D experimental ligand-pocket geometry; 4 folds, 3 calibrators/fold",
                "modes": list(MODES), "max_batch": MAX_ROWS,
                "limitations": [
                    "Native bound-pose experimental geometry is required for 3D inference.",
                    "No arbitrary SMILES or PDB to 423D/704D featurization in this service.",
                    "BioLiP3 was a historical source, and 3D vs shuffled accuracy was inconclusive there.",
                    "OpenBind 2026 shows ranking benefit but REAL 3D RMSE worse than raw 2D.",
                    "Not a production drug-screening or clinical prediction service."
                ]
            })
        return self.send(404, {"error": "Unknown endpoint."})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > MAX_BYTES:
                raise InputError("Body must be nonempty and at most 12 MiB.")
            body = self.rfile.read(size)
            query = parse_qs(urlparse(self.path).query)
            mode = query.get("mode", ["all"])[0]
            if path == "/api/v3/visualize":
                if "application/json" not in self.headers.get("Content-Type", ""):
                    raise InputError("Set Content-Type: application/json.")
                payload = json.loads(body)
                if not isinstance(payload, dict) or set(payload) != {"smiles"}:
                    raise InputError("Provide only a SMILES string for visualization.")
                from preview_geometry import make_preview
                return self.send(200, make_preview(payload["smiles"]))
            if path == "/api/v3/predict":
                if "application/json" not in self.headers.get("Content-Type", ""):
                    raise InputError("Set Content-Type: application/json.")
                payload = json.loads(body)
                if not isinstance(payload, dict):
                    raise InputError("Expected a JSON object.")
                mode = payload.get("mode", mode)
                modes = parse_modes(mode)
                if "sample_id" in payload:
                    if set(payload) - {"sample_id", "mode"}:
                        raise InputError("sample_id requests cannot combine custom feature fields.")
                    if not EXAMPLE.is_file():
                        raise InputError("Local reference examples unavailable.")
                    sid = str(payload["sample_id"])
                    with np.load(EXAMPLE, allow_pickle=False) as z:
                        ids = [str(v) for v in z["ids"].tolist()]
                        if sid not in ids:
                            raise InputError("Unknown sample_id: select one from /api/v3/examples.")
                        ix = ids.index(sid)
                        arrays = {k: z[k][ix:ix + 1] for k in z.files if k != "ids"}
                        arrays["ids"] = np.array([sid])
                    return self.send(200, response_payload(arrays, [sid], modes, "label-free prepared reference"))
                if set(payload) & BLOCKED_LABELS:
                    raise InputError("Outcome labels are forbidden during prediction.")
                arrays = {k: v for k, v in payload.items() if k not in ("mode", "ids")}
                if "ids" in payload:
                    arrays["ids"] = payload["ids"]
                return self.send(200, response_payload(arrays, payload.get("ids"), modes, "uploaded JSON features"))
            if path == "/api/v3/predict-npz":
                if "application/octet-stream" not in self.headers.get("Content-Type", ""):
                    raise InputError("Upload an .npz as application/octet-stream.")
                modes = parse_modes(mode)
                arrays = npz_dict(body)
                return self.send(200, response_payload(arrays, None, modes, "uploaded label-free NPZ"))
            return self.send(404, {"error": "Unknown endpoint."})
        except (InputError, ValueError, TypeError, json.JSONDecodeError, OverflowError) as err:
            return self.send(400, {"error": str(err)})
        except Exception:
            import traceback
            traceback.print_exc()
            return self.send(500, {"error": "Model execution failed; inspect local backend logs."})

    def log_message(self, fmt, *args):
        print(f"[DynaCPI-3D] {self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    host, port = "127.0.0.1", int(os.getenv("DYNACPI_3D_PORT", "8784"))
    print(f"Frozen DynaCPI-3D loaded from {RUN}", flush=True)
    print(f"API listening on http://{host}:{port}/api/v3/health", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
