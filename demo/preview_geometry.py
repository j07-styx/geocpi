"""RDKit ETKDG conformer coordinates for *visualization only*.

These coordinates are not experimental protein-ligand poses and are never
used as inputs to the frozen GeoFuse-CPI affinity checkpoint.
"""
from __future__ import annotations

from functools import lru_cache

from rdkit import Chem
from rdkit.Chem import AllChem, rdMolDescriptors


class PreviewError(ValueError):
    """Invalid or unsupported molecule for a visualization."""


@lru_cache(maxsize=128)
def make_preview(smiles: str) -> dict:
    if not isinstance(smiles, str) or not 1 <= len(smiles.strip()) <= 500:
        raise PreviewError("Enter a SMILES string containing 1–500 characters.")
    source = Chem.MolFromSmiles(smiles.strip())
    if source is None:
        raise PreviewError("RDKit could not parse this SMILES.")
    if source.GetNumHeavyAtoms() > 100:
        raise PreviewError("3D preview supports at most 100 heavy atoms; affinity prediction is unaffected.")
    if source.GetNumHeavyAtoms() == 0:
        raise PreviewError("No heavy atoms to display.")

    # Generate a chemically reasonable gas-phase ligand conformer, not a bound pose.
    mol = Chem.AddHs(source)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    params.maxIterations = 80
    params.numThreads = 1
    result = AllChem.EmbedMolecule(mol, params)
    if result != 0:
        params.useRandomCoords = True
        result = AllChem.EmbedMolecule(mol, params)
    if result != 0:
        raise PreviewError("RDKit could not embed a 3D conformer for this molecule.")
    try:
        if AllChem.UFFHasAllMoleculeParams(mol):
            AllChem.UFFOptimizeMolecule(mol, maxIters=120)
    except Exception:
        pass  # Coordinates remain valid if optional force-field refinement fails.

    conf = mol.GetConformer()
    heavy_count = source.GetNumAtoms()
    positions = [conf.GetAtomPosition(i) for i in range(heavy_count)]
    center = [
        sum(p.x for p in positions) / heavy_count,
        sum(p.y for p in positions) / heavy_count,
        sum(p.z for p in positions) / heavy_count,
    ]
    atoms = [
        {
            "element": source.GetAtomWithIdx(i).GetSymbol(),
            "x": round(p.x - center[0], 5),
            "y": round(p.y - center[1], 5),
            "z": round(p.z - center[2], 5),
        }
        for i, p in enumerate(positions)
    ]
    bonds = [
        {"from": b.GetBeginAtomIdx(), "to": b.GetEndAtomIdx(), "order": int(b.GetBondTypeAsDouble())}
        for b in source.GetBonds()
    ]
    return {
        "status": "ok",
        "canonical_smiles": Chem.MolToSmiles(source, isomericSmiles=True),
        "formula": rdMolDescriptors.CalcMolFormula(source),
        "atoms": atoms,
        "bonds": bonds,
        "conformer_source": "RDKit ETKDGv3 generated gas-phase ligand conformer",
        "is_experimental_bound_pose": False,
        "used_for_affinity_prediction": False,
        "notice": "Illustrative ligand conformation, not a measured bound pose or 3D model input.",
    }
