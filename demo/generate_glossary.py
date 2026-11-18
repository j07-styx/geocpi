"""Build the offline-searchable DAVIS CPI glossary from the public DeepDTA files.

Usage:
  python demo/generate_glossary.py --source C:\\path\\to\\davis
Source directory must contain ligands_can.txt, proteins.txt and Y.
The CID-to-name mapping comes from PubChem PUG REST at generation time.
"""
import argparse
import importlib
import json
import pickle
import urllib.request
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO / "demo" / "frontend" / "public" / "davis-glossary.json"
SOURCE_URL = "https://github.com/hkmztrk/DeepDTA/tree/master/data/davis"


class SafeNumpyUnpickler(pickle.Unpickler):
    ALLOWED = {
        ("numpy.core.multiarray", "_reconstruct"),
        ("numpy", "ndarray"),
        ("numpy", "dtype"),
    }

    def find_class(self, module, name):
        if (module, name) not in self.ALLOWED:
            raise pickle.UnpicklingError("Disallowed pickle class: %s.%s" % (module, name))
        return getattr(importlib.import_module(module), name)


def fetch_pubchem_titles(cids):
    names = {}
    for start in range(0, len(cids), 16):
        chunk = cids[start:start + 16]
        url = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
               + ",".join(chunk) + "/property/Title,IUPACName/JSON")
        request = urllib.request.Request(url, headers={"User-Agent": "GeoFuse-CPI-Glossary/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            records = json.load(response)["PropertyTable"]["Properties"]
        for row in records:
            title = row.get("Title") or row.get("IUPACName")
            if title:
                names[str(row["CID"])] = title
    missing = set(cids) - set(names)
    if missing:
        raise ValueError("PubChem names missing for CIDs: " + ", ".join(sorted(missing)))
    return names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path, help="Directory containing the public DAVIS files")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    ligands = json.loads((args.source / "ligands_can.txt").read_text(encoding="utf-8"))
    proteins = json.loads((args.source / "proteins.txt").read_text(encoding="utf-8"))
    with (args.source / "Y").open("rb") as file:
        values = np.asarray(SafeNumpyUnpickler(file, encoding="latin1").load(), dtype=float)
    if values.shape != (len(ligands), len(proteins)) or len(ligands) != 68 or len(proteins) != 442:
        raise ValueError("Unexpected DAVIS dimensions: %s" % (values.shape,))
    if not np.all(np.isfinite(values)) or not np.all(values > 0):
        raise ValueError("DAVIS contains nonpositive or nonfinite Kd values")

    titles = fetch_pubchem_titles(list(ligands))
    payload = {
        "source": "DeepDTA DAVIS benchmark",
        "sourceUrl": SOURCE_URL,
        "compoundNameSource": "PubChem PUG REST Title (IUPAC name fallback), by CID",
        "affinityUnit": "Kd (nM)",
        "censoringNote": "DAVIS uses 10,000 nM for nonbinding or weak/unobserved pairs; interpret these as a cutoff, not exact Kd measurements.",
        "compounds": [
            {"cid": cid, "name": titles[cid], "smiles": smiles}
            for cid, smiles in ligands.items()
        ],
        "proteins": [
            {"name": name, "sequence": sequence}
            for name, sequence in proteins.items()
        ],
        "kdNm": values.tolist(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print("Created %s (%s bytes): %s compounds x %s proteins = %s pairs" % (
        args.output, args.output.stat().st_size, len(ligands), len(proteins), values.size
    ))
    print("Sample compounds:", ", ".join(titles[cid] for cid in list(ligands)[:7]))
    print("Cutoff entries (Kd=10000 nM):", int(np.sum(values == 10000)))


if __name__ == "__main__":
    main()
