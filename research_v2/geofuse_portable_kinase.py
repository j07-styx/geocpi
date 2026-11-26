from pathlib import Path
import numpy as np,torch
from torch import nn
from rdkit import Chem
from rdkit.Chem import rdFingerprintGenerator
class Unified(nn.Module):
 def __init__(self):
  super().__init__()
  self.p=nn.Sequential(nn.Linear(1280,128),nn.LayerNorm(128),nn.GELU(),nn.Dropout(.15),nn.Linear(128,48),nn.LayerNorm(48))
  self.c=nn.Sequential(nn.Linear(2048,128),nn.LayerNorm(128),nn.GELU(),nn.Dropout(.15),nn.Linear(128,48),nn.LayerNorm(48))
  self.g=nn.Sequential(nn.Linear(128,48,bias=False),nn.GELU(),nn.Linear(48,48,bias=False))
  self.shared=nn.Sequential(nn.Linear(192,96),nn.LayerNorm(96),nn.GELU(),nn.Dropout(.15),nn.Linear(96,48),nn.GELU())
  self.heads=nn.ModuleDict({k:nn.Linear(48,1) for k in ('davis','kiba','metz','gensparc')})
 def forward(self,p,c,g,k):
  p=self.p(p)+self.g(g);c=self.c(c)
  return self.heads[k](self.shared(torch.cat([p,c,p*c,abs(p-c)],1))).squeeze(1)
def unit(x):return x/np.maximum(np.linalg.norm(x,axis=1,keepdims=True),1e-8)
def fingerprints(smiles):
 gen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048,includeChirality=True)
 out=[]
 for s in smiles:
  m=Chem.MolFromSmiles(s)
  if m is None:raise ValueError('Invalid SMILES')
  s=Chem.MolToSmiles(m,isomericSmiles=True);out.append(gen.GetFingerprintAsNumPy(Chem.MolFromSmiles(s)))
 return np.asarray(out,np.float32)
class Predictor:
 def __init__(self,checkpoint,anchors):
  self.ck=torch.load(checkpoint,map_location='cpu',weights_only=True);self.a=np.load(anchors,allow_pickle=False);self.net=Unified();self.net.load_state_dict(self.ck['state_dict']);self.net.eval()
 def predict(self,assay,smiles,embeddings):
  if assay not in ('davis','kiba','metz'):raise ValueError('Use an assay-specific head: davis, kiba, metz')
  p=np.asarray(embeddings,np.float32);c=fingerprints(smiles)
  if p.shape!=(len(c),1280) or not np.isfinite(p).all():raise ValueError('Expected finite ESM2 650M embeddings, 1280 values per pair')
  mu,sd=self.ck['assay_normalization'][assay]
  with torch.inference_mode():n=self.net(torch.tensor(unit(p)*np.sqrt(1280),dtype=torch.float32),torch.tensor(c),torch.zeros((len(c),128)),assay).numpy()*sd+mu
  h=self.ck['similarity_heads'][assay];w=h['kernel_weight'];prefix=assay+'__'
  if assay=='davis':n=np.maximum(n,5)
  if not w:return n
  ap=self.a[prefix+'protein'];ac=self.a[prefix+'chemical'];center=self.a[prefix+'center']
  dot=c@ac.T; cs=dot/np.maximum(c.sum(1)[:,None]+ac.sum(1)[None,:]-dot,1e-6)
  ps=np.clip(unit(p-center)@unit(ap-center).T,-1,1)
  gamma,chem,prot,_=h['config'];k=np.exp(-gamma*(1-ps))
  v=h['mean']+(cs*k+chem*cs+prot*k).astype(np.float32)@h['alpha'].numpy()
  if assay=='davis':v=np.maximum(v,5)
  return (1-w)*n+w*v
