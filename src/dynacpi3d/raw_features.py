"""Compatibility alias for historical imports."""
import sys
from geofuse_cpi import raw_features as _implementation
sys.modules[__name__] = _implementation
