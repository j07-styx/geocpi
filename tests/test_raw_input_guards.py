"""Self-contained raw-manifest fail-closed tests. No model files or assays needed."""
from pathlib import Path
import tempfile,csv,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from predict_raw import read_inputs
def write(p,fields,rows):
 with p.open("w",encoding="utf8",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def must_fail(path):
 try:read_inputs(path)
 except (ValueError,KeyError):return
 raise AssertionError("Unsafe or malformed raw manifest unexpectedly accepted")
def main():
 fields=["sample_id","smiles","ligand_sdf","complex_pdb","assay_type"]
 record={"sample_id":"case1","smiles":"CC(=O)Nc1ccccc1",
  "ligand_sdf":"lig.sdf","complex_pdb":"bound.pdb","assay_type":"KD"}
 with tempfile.TemporaryDirectory() as d:
  file=Path(d)/"raw.csv"
  write(file,fields,[record])
  rows=read_inputs(file)
  assert len(rows)==1 and rows[0]["assay_type"]=="KD"
  assert rows[0]["complex_pdb"]==str((Path(d)/"bound.pdb").resolve())
  write(file,fields, [record,record])
  must_fail(file)
  write(file,fields+["experimental_pKD"],[{**record,"experimental_pKD":"7.0"}])
  must_fail(file)
  write(file,fields+["label"],[{**record,"label":"fake"}])
  must_fail(file)
  write(file,fields,[{**record,"assay_type":"IC50"}])
  must_fail(file)
  write(file,fields,[{**record,"sample_id":""}])
  must_fail(file)
 print("PASS: raw manifest/duplicate-ID/Kd-Y-leakage/assay-type fail-closed tests")
if __name__=="__main__":main()
