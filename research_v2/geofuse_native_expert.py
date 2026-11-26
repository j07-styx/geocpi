from pathlib import Path
import numpy as np,torch,lightgbm as lgb
from torch import nn
class ExplicitPairResidual(nn.Module):
 def __init__(self):
  super().__init__();self.net=nn.Sequential(nn.Linear(704,64),nn.LayerNorm(64),nn.SiLU(),nn.Linear(64,32),nn.SiLU(),nn.Linear(32,1))
 def forward(self,x):return .5*torch.tanh(self.net(x).squeeze(-1))
def predict_native(checkpoint,x2d,geometry):
 # Prepared features only: original V48 423D anchor, NOT unified 48D trunk.
 x=np.asarray(x2d,np.float32)
 assert x.ndim==2 and x.shape[1]==423 and np.isfinite(x).all()
 assert set(geometry)=={'real','shuffled','pocket'}
 for v in geometry.values():assert v.shape==(len(x),704) and np.isfinite(v).all()
 folds={m:[] for m in ('2d','real','shuffled','pocket')}
 for fold in checkpoint['native_geometry_expert']['folds']:
  base=np.mean([lgb.Booster(model_str=s).predict(x,num_threads=2) for s in fold['calibrators']],axis=0)
  folds['2d'].append(base)
  for mode,v in geometry.items():
   c=fold[mode]; net=ExplicitPairResidual();net.load_state_dict(c['state_dict']);net.eval()
   inp=torch.from_numpy(((np.asarray(v,np.float64)-c['mean'].numpy())/c['std'].numpy()).astype(np.float32))
   with torch.no_grad():folds[mode].append(base+c['scale']*net(inp).numpy().astype(float))
 out={m:np.mean(v,axis=0) for m,v in folds.items()};out['raw']=x[:,-1].astype(float)
 return out
