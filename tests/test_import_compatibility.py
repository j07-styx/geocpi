"""New and historical imports must resolve to the same implementation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from geofuse_cpi.model import ExplicitPairResidual
from dynacpi3d.model import ExplicitPairResidual as LegacyResidual
from geofuse_cpi.raw_features import LowRankGeoFuseCPI, LowRankDynaCPI

assert ExplicitPairResidual is LegacyResidual
assert LowRankGeoFuseCPI is LowRankDynaCPI
print("PASS: GeoFuse-CPI and historical import compatibility")
