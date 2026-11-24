"""Compatibility alias for historical imports."""
import sys
from geofuse_cpi import model as _implementation
sys.modules[__name__] = _implementation
