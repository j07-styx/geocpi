"""The exact V16/V17 47,361-parameter 704D residual architecture and 2D calibrator.

Reference originals (read-only, not redistributed):
- geometry_v6_20261115/v16_pairenergy_2Danchored_trainonly_20261116/
  fit_v16_GROUP_OOF_LIGHTGBM_2D_ANCHOR_DIRECT_PAIR_ENERGY_REAL_SHUFFLE_POCKET_FIXED16EP.py
- geometry_v6_20261115/v17_frozen_original_DynaV5_native_pair_704D_HiQBind_TRAIN349_20261116/
  fit_v17_ACTUAL_DYNAV5_423D_2D_ANCHOR_PLUS_NATIVE704D_DIRECT_PAIR_4FOLD_TRAINONLY.py
"""
from torch import nn
import torch


class ExplicitPairResidual(nn.Module):
    """Scaled, bounded correction to an independently calibrated GeoFuse-CPI 2D (v5) 2D prediction."""

    def __init__(self, n_dim=704):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_dim, 64),
            nn.LayerNorm(64),
            nn.SiLU(),
            nn.Linear(64, 32),
            nn.SiLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return 0.5 * torch.tanh(self.net(x).squeeze(-1))


def make_calibrator(seed):
    """V17 LightGBM calibration settings (original old 349-source fourfold experiment)."""
    from lightgbm import LGBMRegressor

    return LGBMRegressor(
        n_estimators=175,
        learning_rate=0.04,
        num_leaves=9,
        max_depth=5,
        min_child_samples=12,
        reg_alpha=0.5,
        reg_lambda=8.0,
        colsample_bytree=0.85,
        subsample=0.9,
        subsample_freq=1,
        n_jobs=3,
        verbosity=-1,
        random_state=int(seed),
    )


def check_architecture():
    """Check byte-level architectural parity in dimensionality and parameter count."""
    net = ExplicitPairResidual()
    count = sum(p.numel() for p in net.parameters())
    if count != 47361:
        raise AssertionError(f"Unexpected residual model parameters: {count}")
    with torch.no_grad():
        out = net(torch.zeros((3, 704), dtype=torch.float32))
    if out.shape != (3,) or not torch.isfinite(out).all():
        raise AssertionError("Residual architecture forward check failed")
    return count
