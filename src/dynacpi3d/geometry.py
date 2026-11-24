"""Compatibility alias for historical imports."""
import sys
from geofuse_cpi import geometry as _implementation
sys.modules[__name__] = _implementation
