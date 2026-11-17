"""Raw SMILES + X-ray bound SDF/PDB -> frozen original DynaCPI v5 features.

Port of the already-frozen research V20/V50 source encoder. No assay labels are
read or accepted. External weights and original DAVIS ligand reference list are
provided explicitly, never packaged in the public repository.
"""
from collections import Counter,defaultdict
from pathlib import Path
import hashlib,json
import numpy as np
import torch
from torch import nn
from scipy.spatial import cKDTree
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator, Descriptors, rdMolDescriptors
from .geometry import pair_features

RDLogger.DisableLog("rdApp.*")
AA="ACDEFGHIKLMNPQRSTVWY"
MAP3={"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C",
      "GLU":"E","GLN":"Q","GLY":"G","HIS":"H","ILE":"I",
      "LEU":"L","LYS":"K","MET":"M","PHE":"F","PRO":"P",
      "SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}
MORGAN=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048,includeChirality=True)
CK_SHA={
 2931:"384a26a788cac972da04d160afb4e57dbc49803f6d52f8f988450aaad3282053",
 2932:"21104f400f488b59868e34b7029f31dc8fadd455f12d1d482a74bd0a00a53d7f"
}
def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def stable_hash(t):
 return int.from_bytes(hashlib.blake2b(t.encode(),digest_size=8).digest(),"little")
def molecular_descriptors(mol):
 fns=[Descriptors.MolWt,Descriptors.MolLogP,Descriptors.TPSA,
  rdMolDescriptors.CalcNumRotatableBonds,rdMolDescriptors.CalcNumHBD,
  rdMolDescriptors.CalcNumHBA,rdMolDescriptors.CalcNumRings,
  rdMolDescriptors.CalcFractionCSP3,rdMolDescriptors.CalcNumAromaticRings,
  rdMolDescriptors.CalcNumAliphaticRings,rdMolDescriptors.CalcNumHeteroatoms,
  rdMolDescriptors.CalcNumHeavyAtoms,rdMolDescriptors.CalcNumSaturatedRings,
  rdMolDescriptors.CalcNumBridgeheadAtoms]
 vals=np.asarray([float(fn(mol)) for fn in fns],dtype=np.float32)
 return np.log1p(np.abs(vals))*np.sign(vals)*np.float32(.1)
def fingerprint(m):
 out=np.zeros(2048,dtype=np.float32)
 DataStructs.ConvertToNumpyArray(MORGAN.GetFingerprint(m),out)
 return out
def chain_geometry(pdb_bytes, ligand_xyz, explicit_chain=""):
 """Protein heavy atoms from ATOM only, native target chain chosen by max contacts."""
 chains=defaultdict(list); ca=defaultdict(dict)
 for s in pdb_bytes.decode("ascii","replace").splitlines():
  if not s.startswith("ATOM  ") or len(s)<54 or s[16:17] not in (" ","A","1"):continue
  res=s[17:20].strip().upper()
  if res not in MAP3:continue
  atom_name=s[12:16].strip()
  elem=s[76:78].strip().title() if len(s)>=78 else atom_name[:1].title()
  if elem in ("H","D",""):continue
  try:
   z=Chem.GetPeriodicTable().GetAtomicNumber(elem)
   xyz=np.array([float(s[k:k+8]) for k in (30,38,46)],dtype=np.float32)
  except (ValueError,RuntimeError):continue
  if not np.isfinite(xyz).all():continue
  ch=s[21:22]
  if explicit_chain and ch!=explicit_chain:continue
  chains[ch].append((xyz,z))
  if atom_name=="CA":
   resid=s[22:27]
   if resid not in ca[ch]:ca[ch][resid]=MAP3[res]
 candidates=[]
 for ch,atoms in chains.items():
  if len(ca[ch])<70:continue
  xyz=np.array([p for p,_ in atoms],dtype=np.float32)
  nearest=cKDTree(xyz).query(ligand_xyz,k=1)[0]
  hits=int(np.count_nonzero(nearest<=8.))
  candidates.append(((hits,len(ca[ch])),ch,atoms))
 if not candidates:raise ValueError("No receptor chain >=70 CA residues with protein ATOM coordinates")
 _,ch,atoms=max(candidates,key=lambda z:z[0])
 seq="".join(ca[ch].values())
 xyz=np.array([p for p,_ in atoms],dtype=np.float32)
 elem=np.array([z for _,z in atoms],dtype=np.int16)
 keep=sorted({int(k) for idx in cKDTree(xyz).query_ball_point(ligand_xyz,8.) for k in idx})
 if len(keep)<10:raise ValueError("Native protein pocket has <10 heavy atoms within 8A")
 pocket=xyz[keep]
 near=cKDTree(pocket).query(ligand_xyz)[0]
 if near.min()<1.55:raise ValueError("Native geometry likely covalent or physically clashing (distance <1.55A)")
 return seq,ch,pocket,elem[keep],xyz
def graph_from_raw(smiles, ligand_sdf, complex_pdb, *, sequence="",receptor_chain="", strict_overlay=True):
 """Verify stereoisomer and SDF coordinates against complex PDB and return V16 graph."""
 s=Path(ligand_sdf).read_bytes()
 end=s.find(b"M  END")
 if end<0:raise ValueError("SDF lacks molecular coordinate block")
 # Critically ignore SDF property annotations; user may include assay fields.
 mol=Chem.MolFromMolBlock(s[:end+6].decode("ascii","replace")+"\n",
  sanitize=True,removeHs=False,strictParsing=False)
 if mol is None:raise ValueError("Cannot parse SDF molecular coordinate block")
 mol=Chem.RemoveHs(mol)
 assert mol.GetNumConformers()==1
 ref=Chem.MolFromSmiles(smiles)
 if ref is None:raise ValueError("Invalid user-supplied SMILES")
 if Chem.MolToSmiles(ref,isomericSmiles=True)!=Chem.MolToSmiles(mol,isomericSmiles=True):
  raise ValueError("SMILES isomeric identity differs from native 3D SDF molecule")
 if mol.GetNumAtoms()<5 or mol.GetNumAtoms()>100 or len(Chem.GetMolFrags(mol))!=1:
  raise ValueError("Ligand heavy atom limits or chemical fragments invalid")
 ligxyz=np.asarray(mol.GetConformer().GetPositions(),dtype=np.float32)
 if not np.isfinite(ligxyz).all():raise ValueError("Ligand coordinates contain NaN")
 edges=np.asarray([(b.GetBeginAtomIdx(),b.GetEndAtomIdx()) for b in mol.GetBonds()],dtype=np.int32)
 if edges.shape[0]<mol.GetNumAtoms()-1:raise ValueError("Ligand bond graph incomplete")
 bonds=edges.T
 pdb=Path(complex_pdb).read_bytes()
 seq,chosen,pocket,pz,_=chain_geometry(pdb,ligxyz,explicit_chain=receptor_chain)
 if sequence and seq!=sequence:raise ValueError("Provided protein sequence differs from original PDB CA sequence")
 if strict_overlay:
  het=[]
  for line in pdb.decode("ascii","replace").splitlines():
   if not line.startswith("HETATM") or len(line)<54:continue
   if line[17:20].strip().upper() in ("HOH","WAT","DOD"):continue
   symbol=line[76:78].strip().upper() if len(line)>=78 else line[12:16].strip()[:1].upper()
   if symbol in ("H","D"):continue
   try:pos=[float(line[k:k+8]) for k in (30,38,46)]
   except ValueError:continue
   if np.isfinite(pos).all():het.append(pos)
  if not het or np.mean(cKDTree(np.asarray(het)).query(ligxyz)[0]<=.3)<.95:
   raise ValueError("SDF ligand heavy-atom pose does not overlay complex PDB HETATM")
 graph={"ligand_xyz":ligxyz,"ligand_z":np.array([a.GetAtomicNum() for a in mol.GetAtoms()],dtype=np.int16),
  "ligand_bonds":bonds,"pocket_xyz":pocket,"pocket_z":pz}
 geometry={mode:pair_features(graph,mode) for mode in ("real","shuffled","pocket")}
 return {"sequence":seq,"chain":chosen,"fingerprint":fingerprint(ref),
  "side":side_features(ref,seq),"geometry":geometry,"ligand_heavy_atoms":int(mol.GetNumAtoms()),
  "pocket_heavy_atoms":len(pocket)}
def side_features(mol,seq,assay_type="KD"):
 counts=Counter(seq)
 comp=np.array([counts.get(a,0)/len(seq) for a in AA],dtype=np.float32)*20
 trig=np.zeros(128,dtype=np.float32)
 for k in range(len(seq)-2):trig[stable_hash(seq[k:k+3])%128]+=1
 trig/=max(float(trig.sum()),1)
 assay=np.array([assay_type.upper()=="KI",assay_type.upper()=="KD",0,0],dtype=np.float32)
 side=np.concatenate((comp,trig*20,molecular_descriptors(mol),assay))
 assert side.shape==(166,)
 return side.astype(np.float32)
class LowRankDynaCPI(nn.Module):
 """Exact original DAVIS v5 architecture from original train_full_davis_v5.py."""
 def __init__(self):
  super().__init__()
  self.protein=nn.Sequential(nn.Linear(1280,96),nn.LayerNorm(96),nn.GELU(),nn.Dropout(.15),
   nn.Linear(96,32),nn.LayerNorm(32))
  self.chemical=nn.Sequential(nn.Linear(2048,128),nn.LayerNorm(128),nn.GELU(),nn.Dropout(.15),
   nn.Linear(128,32),nn.LayerNorm(32))
  self.head=nn.Sequential(nn.Linear(128,64),nn.GELU(),nn.Dropout(.15),nn.Linear(64,1))
def esm_mean(seqs,esm_checkpoint,device="auto"):
 """Original 512-token windows, 128-token overlap, terminal half weights."""
 import esm,os
 esm_checkpoint=Path(esm_checkpoint)
 if not esm_checkpoint.is_file():raise FileNotFoundError(esm_checkpoint)
 if sha(esm_checkpoint)!="ea9d0522b335a8778dea6535a65301f10208dece28cd5865482b0b1fc446168c":
  raise ValueError("Only original SHA-verified ESM2-t33-650M checkpoint accepted")
 regression=esm_checkpoint.with_name(esm_checkpoint.stem+"-contact-regression.pt")
 if regression.exists() and sha(regression)!="8ffe6edbd4173dc8d45c2cd5cb27d43aad77ec26b4c768200c58ae1f96693575":
  raise ValueError("Original ESM contact regression file checksum mismatch")
 # fair-esm 2.0.0 uses torch.load without weights_only. We allow its trusted
 # original hash-verified checkpoint only, not arbitrary user-supplied files.
 prev=os.environ.get("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD")
 os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"]="1"
 try:
  model,alphabet=esm.pretrained.load_model_and_alphabet_local(str(esm_checkpoint))
 finally:
  if prev is None:os.environ.pop("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD",None)
  else:os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"]=prev
 model=model.eval()
 gpu=device=="cuda" or (device=="auto" and torch.cuda.is_available())
 device_obj="cuda" if gpu else "cpu"
 model=model.to(device_obj)
 if gpu:model=model.half()
 conv=alphabet.get_batch_converter()
 answer={}
 for seq in sorted(set(seqs)):
  numer=np.zeros(1280,dtype=np.float64);denom=0.
  for offset in range(0,len(seq),384):
   fragment=seq[offset:offset+512]
   if not fragment:break
   _,_,tokens=conv([("DynaCPI_native_sequence",fragment)])
   with torch.inference_mode():
    x=model(tokens.to(device_obj),repr_layers=[33],return_contacts=False)["representations"][33][0,1:len(fragment)+1].float().cpu().numpy()
   weights=np.ones(len(fragment),dtype=np.float64)
   if offset>0:weights[:min(128,len(fragment))]*=.5
   if offset+len(fragment)<len(seq):weights[-min(128,len(fragment)):]*=.5
   numer+=(x.astype(np.float64)*weights[:,None]).sum(0);denom+=float(weights.sum())
   if offset+len(fragment)>=len(seq):break
  vec=(numer/denom).astype(np.float32)
  if vec.shape!=(1280,) or not np.isfinite(vec).all():raise ValueError("ESM2 embedding invalid")
  answer[seq]=vec
 return answer
def backbone_context(fingerprints,esm_vectors,side_vectors,davis_ligands,checkpoint2931,checkpoint2932):
 """Frozen original two-member v5 tower context422 and raw prediction."""
 source=json.loads(Path(davis_ligands).read_text("utf8"))
 if len(source)!=68:raise ValueError("Original DAVIS source expected exactly 68 ligand entries")
 fp68=[]
 for smi in source.values():
  m=Chem.MolFromSmiles(smi)
  if m is None:raise ValueError("Original DAVIS reference molecule malformed")
  fp68.append(fingerprint(m))
 fpd=np.stack(fp68).astype(np.float32)
 fps=np.stack(fingerprints).astype(np.float32)
 protein=np.stack(esm_vectors).astype(np.float32)
 sides=np.stack(side_vectors).astype(np.float32)
 assert fps.shape[1]==2048 and protein.shape[1]==1280 and sides.shape[1]==166
 dot=fps@fpd.T
 den=fps.sum(1,keepdims=True)+fpd.sum(1)[None,:]-dot
 similarity=np.divide(dot,den,out=np.zeros_like(dot),where=den>0)
 towers=[];preds=[];hashes={}
 torch.set_num_threads(3)
 for seed,path in ((2931,checkpoint2931),(2932,checkpoint2932)):
  if sha(path)!=CK_SHA[seed]:raise ValueError("Authentic DAVIS seed checkpoint hash mismatch")
  # These are trusted ORIGINAL local checkpoint files, not arbitrary user input.
  checkpoint=torch.load(path,map_location="cpu",weights_only=False)
  if checkpoint["format"]!="dynacpi_v5_full_davis_20261109":
   raise ValueError("Original DynaCPI checkpoint format mismatch")
  model=LowRankDynaCPI().cpu().eval()
  model.load_state_dict(checkpoint["state_dict"])
  normalized=np.clip((protein-np.asarray(checkpoint["pfeat_mu"],np.float32))/
    np.asarray(checkpoint["pfeat_scale"],np.float32),-6,6).astype(np.float32)
  with torch.inference_mode():
   pt=model.protein(torch.from_numpy(normalized))
   lg=model.chemical(torch.from_numpy(fps))
   latent=torch.cat((lg,pt,lg*pt,torch.abs(lg-pt)),dim=1)
   resid=model.head(latent).squeeze(1).numpy()
  prior=float(checkpoint["chemical_kernel_intercept"])+similarity@np.asarray(checkpoint["chemical_kernel_coef"],np.float32)
  prediction=(prior+float(checkpoint["training_label_sd"])*resid).astype(np.float32)
  towers.append(latent.numpy().astype(np.float32));preds.append(prediction)
  hashes[str(seed)]=sha(path)
 context=np.concatenate((towers[0],towers[1],sides),axis=1).astype(np.float32)
 raw=np.mean(preds,axis=0).astype(np.float32)
 assert context.shape==(len(fps),422) and raw.shape==(len(fps),)
 return context,raw,hashes
