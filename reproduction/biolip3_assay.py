"""Original independent assay parser; no source rows or label values."""
import re,math
import numpy as np
SCALE={"PM":12,"NM":9,"UM":6,"MM":3,"M":0}
TAG=re.compile(r"(?i)\b(Ki|Kd)\s*=(?!=)")
VALUE=re.compile(r"(?i)\b(Ki|Kd)\s*=\s*([0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE]([+-]?[0-9]+))?\s*(pM|nM|uM|µM|μM|mM|M)\b")
def independent_y(row,kind):
 vals=[]
 for text in row[13:17]:
  tags=[m.group(1).upper() for m in TAG.finditer(text) if m.group(1).upper()==kind]
  matches=[m for m in VALUE.finditer(text) if m.group(1).upper()==kind]
  if len(tags)!=len(matches):raise AssertionError("Originally accepted new experimental row now has missing-unit tag")
  for m in matches:
   if any(c in text[max(0,m.start()-3):m.start()] for c in "<>~≈≤≥"):
    raise AssertionError("Originally accepted row was censored")
   val=float(m.group(2))
   if m.group(3):val*=10**int(m.group(3))
   unit=m.group(4).replace("µ","u").replace("μ","u").upper()
   if not val>0:raise AssertionError("Invalid original experimental Y")
   valp=-math.log10(val)+SCALE[unit]
   if not 2<=valp<=13:raise AssertionError("Original experiment assay out of permitted log range")
   vals.append(valp)
 if not vals or max(vals)-min(vals)>.3:raise AssertionError("Originally accepted row now conflicts")
 return float(np.median(vals))
