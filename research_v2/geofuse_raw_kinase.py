from pathlib import Path
import hashlib,re,threading
import numpy as np,torch
from geofuse_portable_kinase import Predictor
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def clean(sequence):
 if not isinstance(sequence,str):raise ValueError('Protein sequence must be text')
 lines=[x.strip() for x in sequence.splitlines() if x.strip()]
 if sum(x.startswith('>') for x in lines)>1:raise ValueError('One protein at a time')
 s=''.join(''.join(x.split()) for x in lines if not x.startswith('>')).upper()
 if not 1<=len(s)<=2048 or set(s)-set('ACDEFGHIKLMNPQRSTVWYX'):raise ValueError('Expected 1-2048 supported amino acids')
 return s
class Encoder:
 def __init__(self,path):
  self.path=Path(path);self.model=None;self.lock=threading.Lock()
 def init(self):
  if self.model is not None:return
  import esm
  assert sha(self.path)=='ea9d0522b335a8778dea6535a65301f10208dece28cd5865482b0b1fc446168c','Unexpected public ESM checkpoint'
  # Trusted, hash-pinned public checkpoint; map storage to avoid duplicate resident weights.
  data=torch.load(self.path,map_location='cpu',weights_only=False,mmap=True)
  regression=self.path.with_name(self.path.stem+'-contact-regression.pt')
  if regression.is_file():
   # Not used: contacts are never requested. Omit the contact regression entirely.
   pass
  with torch.device('meta'):
   model,alphabet,state=esm.pretrained._load_model_and_alphabet_core_v2(data)
  report=model.load_state_dict(state,strict=False,assign=True)
  assert not report.unexpected_keys and set(report.missing_keys)<= {'contact_head.regression.weight','contact_head.regression.bias'},report
  # ESM rotary inverse-frequency buffers are persistent in this checkpoint; check all used buffers.
  assert all(not v.is_meta for k,v in model.named_buffers()),[(k,v.is_meta) for k,v in model.named_buffers()]
  assert all(not v.is_meta for k,v in model.named_parameters() if not k.startswith('contact_head.'))
  self.model=model.eval();self.convert=alphabet.get_batch_converter()
  del state,data
 def encode(self,sequence):
  s=clean(sequence)
  with self.lock,torch.inference_mode():
   self.init(); n=len(s); acc=torch.zeros(n,1280);count=torch.zeros(n,1)
   for start in range(0,n,872):
    end=min(start+1000,n);_,_,tok=self.convert([('query',s[start:end])])
    r=self.model(tok,repr_layers=[33],return_contacts=False)['representations'][33][0,1:1+end-start].float()
    acc[start:end]+=r;count[start:end]+=1
    if end==n:break
   x=(acc/count).half().float().mean(0).numpy()
   if not np.isfinite(x).all():raise ValueError('Nonfinite embedding')
   return x
def predict_raw(predictor,encoder,assay,smiles,sequence):
 return float(predictor.predict(assay,[smiles],encoder.encode(sequence)[None,:])[0])
