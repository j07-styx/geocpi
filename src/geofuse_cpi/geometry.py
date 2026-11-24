"""V16 direct pairwise geometry features for an explicit energy correction.
Only source ATOM3D original TRAIN's already verified ligand covalent
bond graph and experimentally deposited bound protein pocket coordinates.
All features are rigid-motion invariant and (for REAL + POCKET-only)
permutation invariant with ligand bond indices remapped. Shuffled
negative control destroys atom-pair metric correspondence, and its
assignment depends on source edge ordering.

Feature 704D:
 - 49 ligand/protein atom-element class pair contact fractions
 - 49x10 Gaussian radial histograms directly indexed by pair class
 - 49x3 Gaussian *bond-to-contact angular* histograms by pair class
 - global radial (10) and angular (3) means
 - log1p ligand heavy atoms, pocket heavy atoms, 8A contact count (3)
 - direct mean distance and 10th percentile distance scalars (2).
No numeric experimental affinities are read or used here.
"""
import numpy as np
from scipy.spatial import cKDTree
RADIAL_CENTERS=np.array([1.6,2.2,2.8,3.4,4.0,4.7,5.4,6.2,7.0,7.8],dtype=np.float32)
ANGULAR_CENTERS=np.array([.15,.5,.85],dtype=np.float32)
FEATURE_DIM=49+49*10+49*3+10+3+3+2
assert FEATURE_DIM==704
def element_class(z):
 z=np.asarray(z,dtype=np.int16)
 out=np.full(z.shape,6,dtype=np.int16)
 out[z==6]=0;out[z==7]=1;out[z==8]=2;out[z==16]=3;out[z==15]=4
 out[np.isin(z,[9,17,35,53])]=5
 return out
def pair_features(graph,mode):
 """Return one 704d source-only native bound-pocket geometry summary."""
 if mode not in ("real","shuffled","pocket"):
  raise ValueError("Unknown original source pair geometry mode")
 lx=np.asarray(graph["ligand_xyz"],dtype=np.float32)
 px=np.asarray(graph["pocket_xyz"],dtype=np.float32)
 le=element_class(graph["ligand_z"]);pe=element_class(graph["pocket_z"])
 bonds=np.asarray(graph["ligand_bonds"],dtype=np.int32)
 pocket_tree=cKDTree(px)
 pairs=pocket_tree.query_ball_point(lx,8.0)
 li=np.repeat(np.arange(len(lx),dtype=np.int32),
              np.array([len(t) for t in pairs],dtype=np.int32))
 pj=np.fromiter((k for one in pairs for k in one),dtype=np.int32,count=sum(len(t) for t in pairs))
 count=len(li)
 if not count:
  raise ValueError("Source pocket has no valid heavy contact pair <=8A")
 disp=px[pj]-lx[li]
 dst=np.linalg.norm(disp,axis=1)
 if not (np.isfinite(dst).all() and dst.max()<=8.001):
  raise AssertionError("Native PDB source 8A contact edge nonfinite")
 types=le[li]*7+pe[pj]
 # Precompute source-independent ligand covalent-neighbor directional
 # vectors as bonds, symmetrically, regardless of original bond order.
 nb=[[] for _ in range(len(lx))]
 for i,j in bonds.T:
  nb[int(i)].append(int(j));nb[int(j)].append(int(i))
 ang=np.empty(count,dtype=np.float32)
 for idx in np.unique(li):
  rows=np.where(li==idx)[0]
  b=nb[int(idx)]
  if not b:
   ang[rows]=.5
   continue
  dirs=lx[np.asarray(b,dtype=np.int32)]-lx[idx]
  dirs=dirs/np.maximum(np.linalg.norm(dirs,axis=1,keepdims=True),1e-6)
  u=disp[rows]/np.maximum(dst[rows,None],1e-6)
  # cos^2 is invariant to original bond direction signs and joint E(3)
  # rotation/reflection; average across all covalent heavy-atom neighbors.
  ang[rows]=np.mean(np.square(u@dirs.T),axis=1)
 ang=np.clip(ang,0,1)
 if mode=="shuffled":
  # Pair metric+angle information shuffled together; preserves
  # actual source distributions but not chemical type coupling.
  shift=count//2
  dst_use=np.roll(dst,shift=shift)
  ang_use=np.roll(ang,shift=shift)
 elif mode=="pocket":
  # Exact native topology and chemical identities preserved, metric
  # replaced by constant; source original 8A contact selection remains.
  dst_use=np.full_like(dst,4.5)
  ang_use=np.full_like(ang,.5)
 else:
  dst_use=dst;ang_use=ang
 rbf=np.exp(-.5*np.square((dst_use[:,None]-RADIAL_CENTERS[None,:])/.55))
 abb=np.exp(-.5*np.square((ang_use[:,None]-ANGULAR_CENTERS[None,:])/.18))
 freq=np.bincount(types,minlength=49).astype(np.float32)/count
 rh=np.zeros((49,10),dtype=np.float32)
 ah=np.zeros((49,3),dtype=np.float32)
 np.add.at(rh,types,rbf);np.add.at(ah,types,abb)
 rh/=count;ah/=count
 globrad=rbf.mean(0);globang=abb.mean(0)
 vals=np.concatenate([freq,rh.ravel(),ah.ravel(),globrad,globang,
  np.log1p(np.array([len(lx),len(px),count],dtype=np.float32)),
  np.array([dst_use.mean(),np.quantile(dst_use,.1)],dtype=np.float32)]).astype(np.float32)
 if len(vals)!=704 or not np.isfinite(vals).all():
  raise AssertionError("Direct geometry feature shape/finite check failed")
 return vals
