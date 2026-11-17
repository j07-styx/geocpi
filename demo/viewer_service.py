"""Lightweight local ligand visualization service, independent of affinity model.

No protein-pocket input, no docking, no ML weights: only RDKit conformer geometry.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from preview_geometry import make_preview, PreviewError


class Handler(BaseHTTPRequestHandler):
    def respond(self, status: int, data: dict):
        raw = json.dumps(data, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/viewer/health":
            return self.respond(200, {"status": "ok", "service": "geofuse-ligand-visualizer"})
        self.respond(404, {"error": "Unknown route."})

    def do_POST(self):
        if self.path != "/api/viewer/geometry":
            return self.respond(404, {"error": "Unknown route."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 4096:
                raise PreviewError("Request must contain a SMILES and be less than 4 KB.")
            if "application/json" not in self.headers.get("Content-Type", ""):
                raise PreviewError("Expected a JSON request.")
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict) or set(body) != {"smiles"}:
                raise PreviewError("Only a smiles field is accepted.")
            result = make_preview(body["smiles"])
            self.respond(200, result)
        except (PreviewError, ValueError, TypeError) as exc:
            self.respond(400, {"error": str(exc)})
        except Exception:
            import traceback
            traceback.print_exc()
            self.respond(500, {"error": "Could not generate a molecule preview."})

    def log_message(self, fmt: str, *args):
        print("[GeoFuse viewer] " + fmt % args, flush=True)


if __name__ == "__main__":
    print("Ligand preview at http://127.0.0.1:8785/api/viewer/health", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8785), Handler).serve_forever()
