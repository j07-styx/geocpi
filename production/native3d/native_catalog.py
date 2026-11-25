"""Read-only, label-free native structure retrieval. No model fitting or prediction."""
from __future__ import annotations
import csv, hashlib, json, os, re, zipfile
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import numpy as np
from rdkit import Chem

DEFAULT_ROOT=Path.home()/"GeoFuse-CPI-Pair3D-Experimental/pair3d_experiment/runs/v151_retrieval_catalog_20261120"
EXPECTED="58de8f90f266b4d998db1f4a8bd931ea3aa0e043f26b56e77befc2934f7b49fb"
PREFIX="/api/geocpi/structures"
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def canonical(s):
    if not isinstance(s,str) or not 1<=len(s)<=500:raise ValueError("Invalid SMILES length")
    m=Chem.MolFromSmiles(s)
    if m is None:raise ValueError("Invalid SMILES")
    return Chem.MolToSmiles(m,isomericSmiles=True)
def sequence(s):
    s="".join(l.strip() for l in s.splitlines() if not l.startswith(">")).upper()
    if not 1<=len(s)<=2048 or any(x not in "ACDEFGHIKLMNPQRSTVWYX" for x in s):raise ValueError("Invalid sequence")
    return s
def pair(s,q):
    return hashlib.sha256((s+"|"+q).encode()).hexdigest()
def normalized_resnum(s):
    try:return str(int(s))
    except (ValueError,TypeError):return str(s or "")
def metadata_names(records):
    """Source-provided names/identifiers only; never extract numeric affinity."""
    path=Path.home()/"DynaCPI-3D-RnD/geometry_v6_20261115/bound_complex_v1/hiqbind_sm_metadata.csv"
    wanted={a["structure_id"].upper() for a in records if a["source"].startswith("HIQBIND")}
    byid=defaultdict(list)
    if not path.is_file():return byid
    with path.open(encoding="utf-8-sig",newline="") as f:
        for x in csv.DictReader(f):
            p=x["PDBID"].strip().upper()
            if p in wanted:
                byid[p].append({k:x[k] for k in ["Ligand Name","Ligand Chain","Ligand Residue Number","Ligand SMILES","Protein UniProtID","Protein UniProtName"]})
    return byid
def native_coordinates(raw):
    # Do not export REMARKs, SDF properties, or affinity metadata.
    lines=[l for l in raw.decode("ascii","replace").splitlines() if l.startswith(("ATOM  ","HETATM","TER   ","CONECT","MODEL ","ENDMDL"))]
    if not any(l.startswith(("ATOM  ","HETATM")) for l in lines):raise ValueError("No deposited atoms")
    return "\n".join(lines)+"\nEND\n"
def ccd_name(path,expected):
    # CCD component name, not a guessed common name. Only parse simple quoted values.
    if not path:return None
    try:
        s=Path(path).read_text(encoding="utf8",errors="replace")
        if not re.search(r"(?m)^_chem_comp.id\s+"+re.escape(expected)+r"\s*$",s):return None
        m=re.search(r"(?m)^_chem_comp.name[ \t]+([^\r\n]+)",s)
        if not m:return None
        name=m.group(1).strip().strip("'\"")
        return name if name and name not in (".","?",";") and len(name)<=300 else None
    except OSError:return None

class NativeCatalog:
    def __init__(self,model_pairs,model_ids,root=None):
        self.root=Path(root or os.environ.get("GEOFUSE_NATIVE_CATALOG",str(DEFAULT_ROOT)))
        self.records=[];self.public=[];self.bykey=defaultdict(list);self.bycanonical=defaultdict(list);self.byid={};self.bystructure=defaultdict(list);self.error=None
        self.model_pairs=model_pairs;self.model_ids=set(model_ids)
        if not self.root.is_dir():self.error="Local retrieval catalog not installed";return
        p=self.root/"CATALOG_NOY.json";index=self.root/"PAIR_INDEX_NOY.json";stats=json.loads((self.root/"RESULT.json").read_text())
        assert sha(p)==stats["catalog_sha"] and sha(index)==stats["index_sha"],"Catalog integrity failure"
        if self.root.resolve()==DEFAULT_ROOT.resolve():assert sha(p)==EXPECTED
        records=json.loads(p.read_text());ix=json.loads(index.read_text())
        assert len(records)==stats["structure_records"]
        names=metadata_names(records);namecache={}
        for i,a in enumerate(records):
            assert a["retrieval_only"] and not a["experimental_affinity_exported"]
            sm=a["smiles"];q=a["observed_receptor_sequence"];k=pair(sm,q);assert k==a["pair_key"]
            # Preserve the source-keyed index for integrity, and build a canonical-SMILES alias index for user lookups.
            ck=pair(canonical(sm),sequence(q))
            ident=a["structure_id"];rid=a["source"]+":"+ident;assert rid not in self.byid
            self.byid[rid]=i;self.bystructure[ident].append(i);self.bykey[k].append(i);self.bycanonical[ck].append(i)
            source=a["source"];assets=a["assets"]
            label="OpenBind" if source.startswith("OPENBIND") else "ATOM3D" if source.startswith("ATOM3D") else "OpenPLBind" if source.startswith("OPENPLBIND") else "HiQBind"
            ccd=a.get("ligand_ccd");protein=None;uid=None
            if source.startswith("HIQBIND"):
                good=[]
                for n in names.get(ident.upper(),[]):
                    if n["Ligand Name"].strip().upper()!=ccd or n["Ligand Chain"].strip()!=a.get("ligand_chain") or normalized_resnum(n["Ligand Residue Number"])!=normalized_resnum(a.get("ligand_resnum")):continue
                    try:
                        if canonical(n["Ligand SMILES"])==sm:good.append((n["Protein UniProtID"].strip(),n["Protein UniProtName"].strip()))
                    except ValueError:pass
                if len(set(good))==1:uid,protein=good[0]
            if source.startswith("OPENBIND"):protein="Coxsackievirus A16 2A protease (OpenBind surrogate)"
            if ccd and ccd not in namecache:
                cname=ccd_name(assets.get("ccd_cif"),ccd)
                if cname:namecache[ccd]=cname
            compound=namecache.get(ccd) or ("CCD "+ccd if ccd else "Experimental compound "+ident)
            pred=(sm,q) in model_pairs
            self.public.append(dict(record_id=rid,structure_id=ident,source=label,source_record=source,smiles=sm,sequence=q,entity_sequence=a.get("entity_sequence"),sequence_match=a.get("sequence_match","observed_chain"),compound_name=compound,ligand_ccd=ccd,protein_name=protein or None,uniprot_id=uid or None,receptor_chain=a.get("receptor_chain"),ligand_chain=a.get("ligand_chain"),ligand_resnum=a.get("ligand_resnum"),chemical_identity=a["chemistry"],representation="native_binding_pocket_graph" if "native_pocket_graph_npz" in assets else "deposited_coordinate_file",prediction_supported=pred,prediction_scope="existing frozen model exact input pair" if pred else "retrieval only; no validated fused inference",experimental_affinity=None,assay_construct_verified=False,source_url="https://zenodo.org/records/20026661" if label=="OpenBind" else "https://www.rcsb.org/structure/"+ident))
        assert dict(self.bykey)==ix,"Pair index integrity failure"
        self.records=records
        self.searchable=[" ".join(str(a.get(k) or "") for k in ("structure_id","compound_name","protein_name","uniprot_id","ligand_ccd","smiles","source")).casefold() for a in self.public]
        self.stats=dict(structural_records=len(records),unique_pairs=len(self.bykey),unique_compounds=len({a["smiles"] for a in self.public}),unique_observed_sequences=len({a["sequence"] for a in self.public}),sources=dict(Counter(a["source"] for a in self.public)),prediction_supported_records=sum(a["prediction_supported"] for a in self.public),source_protein_names=sum(bool(a["protein_name"]) for a in self.public),ccd_names=sum(bool(a["ligand_ccd"]) and not a["compound_name"].startswith("CCD ") for a in self.public),numeric_affinity_exported=False,scope="Exact canonical source SMILES plus observed receptor sequence; not assay construct certification")
    def status(self):
        if self.error:return {"status":"unavailable","error":self.error}
        return {"status":"ok",**self.stats}
    def search(self,q="",source="",page=1,limit=20):
        if len(q)>200 or source not in ("","HiQBind","ATOM3D","OpenBind","OpenPLBind") or not 1<=page<=100000 or not 1<=limit<=50:raise ValueError("Invalid search or page limit")
        needle=q.strip().casefold()
        hits=[i for i,a in enumerate(self.public) if (not source or a["source"]==source) and (not needle or needle in self.searchable[i])]
        start=(page-1)*limit
        return {"records":[self.public[i] for i in hits[start:start+limit]],"total":len(hits),"page":page,"limit":limit}
    def lookup(self,sm,q):
        sm=canonical(sm);q=sequence(q)
        hits=self.bycanonical.get(pair(sm,q),[])
        return {"records":[self.public[i] for i in hits],"matched_structures":len(hits),"prediction_supported":(sm,q) in self.model_pairs,"match_basis":"canonicalized exact SMILES and exact observed chain sequence","geometry_generated":False}
    def geometry(self,ident):
        if ident in self.byid:i=self.byid[ident]
        elif len(self.bystructure.get(ident,[]))==1:i=self.bystructure[ident][0]
        elif ident in self.bystructure:raise ValueError("Ambiguous PDB ID; use source-qualified record_id from search")
        else:raise KeyError("Unknown structure ID")
        a=self.records[i];p=self.public[i];assets=a["assets"]
        result={"record":p,"geometry_generated":False}
        if "native_pocket_graph_npz" in assets:
            f=Path(assets["native_pocket_graph_npz"]);assert sha(f)==assets["sha256"]
            with np.load(f,allow_pickle=False) as z:
                lx,px=z["ligand_xyz"],z["pocket_xyz"];lz,pz=z["ligand_atom_features"][:,0],z["pocket_atom_features"][:,0];edges=z["ligand_bonds"]
                assert lx.ndim==2 and px.ndim==2 and lx.shape[1]==px.shape[1]==3 and np.isfinite(lx).all() and np.isfinite(px).all() and len(lx)==len(lz) and len(px)==len(pz)
                result.update(format="native_pocket_graph",ligand_xyz=lx.tolist(),pocket_xyz=px.tolist(),ligand_atomic_numbers=lz.tolist(),pocket_atomic_numbers=pz.tolist(),ligand_bonds=edges.T.tolist())
        elif "native_pdb" in assets:
            f=Path(assets["native_pdb"])
            if "pdb_sha256" in assets:assert sha(f)==assets["pdb_sha256"]
            if f.stat().st_size>20000000:raise ValueError("Structure exceeds size limit")
            result.update(format="pdb",pdb=native_coordinates(f.read_bytes()),notice="Deposited coordinate file may include other chains and ligands; annotated ligand instance and receptor metadata are provided separately.")
        else:
            with zipfile.ZipFile(assets["zip"]) as z:
                for k in ("native_pdb_member","native_sdf_member"):
                    if z.getinfo(assets[k]).file_size>20000000:raise ValueError("Structure exceeds size limit")
                raw=z.read(assets["native_sdf_member"]);end=raw.find(b"M  END");assert end>=0
                result.update(format="pdb",pdb=native_coordinates(z.read(assets["native_pdb_member"])),ligand_molblock=raw[:end+6].decode("ascii","replace")+"\n",notice="Deposited native complex and ligand coordinates; SDF metadata removed.")
        return result
    def handle(self,handler):
        u=urlsplit(handler.path);params=parse_qs(u.query,keep_blank_values=True)
        def get(k,default=""):
            v=params.get(k,[default])
            if len(v)!=1:raise ValueError("Duplicate query parameter")
            return v[0]
        try:
            if u.path==PREFIX+"/status":return handler.respond(200,self.status())
            if self.error:return handler.respond(503,self.status())
            if u.path==PREFIX+"/search":return handler.respond(200,self.search(get("q"),get("source"),int(get("page","1")),int(get("limit","20"))))
            if u.path==PREFIX+"/lookup":return handler.respond(200,self.lookup(get("smiles"),get("sequence")))
            if u.path==PREFIX+"/geometry":return handler.respond(200,self.geometry(get("id")))
            return handler.respond(404,{"error":"Unknown structure route"})
        except KeyError:return handler.respond(404,{"error":"Unknown structure ID"})
        except (ValueError,TypeError,OverflowError) as e:return handler.respond(400,{"error":str(e)})
        except Exception:return handler.respond(503,{"error":"Native structure data unavailable or failed integrity check"})

