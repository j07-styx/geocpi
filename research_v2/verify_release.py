from pathlib import Path
import argparse,hashlib,io,json,zipfile,tempfile
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');args=ap.parse_args()
lock=json.loads((p/'RELEASE_MANIFEST.json').read_text())
for k,v in lock['files'].items():assert sha((p/k).read_bytes())==v,k
r=json.loads((p/'PAPER_RESULTS.json').read_text());a=json.loads((p/'NATIVE_ACCURACY_AUDIT.json').read_text())
assert a['checkpoint_sha']==r['checkpoint_sha'] and a['prediction_sha']==r['prediction_sha']
with zipfile.ZipFile(p/'geofuse-cpi-v2-inference.zip') as z:
 m=json.loads(z.read('manifest.json'))
 assert set(z.namelist())==set(m['files'])|{'manifest.json'}
 for k,v in m['files'].items():assert sha(z.read(k))==v,k
 assert m['files']['GEOFUSE_CPI_V2.pt']==r['checkpoint_sha'] and m['files']['PRED_NOY.npz']==r['prediction_sha']
 if args.smoke:
  import numpy as np,torch
  from geofuse_portable_kinase import Predictor
  from geofuse_native_expert import predict_native
  torch.set_num_threads(2)
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);z.extract('GEOFUSE_CPI_V2.pt',t);z.extract('TRAIN_ANCHORS_NO_Y.npz',t)
   pred=Predictor(t/'GEOFUSE_CPI_V2.pt',t/'TRAIN_ANCHORS_NO_Y.npz')
   x=np.random.default_rng(2931).standard_normal((1,1280)).astype(np.float32)
   for assay in ('davis','kiba','metz'):
    y=pred.predict(assay,['CC(=O)Oc1ccccc1C(=O)O'],x);assert y.shape==(1,) and np.isfinite(y).all()
   # Use a real label-free feature row from the existing native bundle, not a fabricated physical pose.
   with zipfile.ZipFile(p.parent/'reproduction/openbind-replay.zip') as native:
    with np.load(io.BytesIO(native.read('features.npz')),allow_pickle=False) as f:
     y=predict_native(pred.ck,f['x2d'][:1],{k:f[k][:1] for k in ('real','shuffled','pocket')})
     assert all(np.isfinite(v).all() for v in y.values())
   pred.a.close()
print('PASS: one checkpoint, label-free bundle and result ledger verified.')
