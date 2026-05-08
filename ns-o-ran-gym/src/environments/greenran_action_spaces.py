"""
GreenRAN Action Spaces.

Wraps the RSLAQ action-space logic with GreenRAN defaults.
The action representation is identical (3 slices -> PRB percentages),
so we just re-export the functions with updated docstrings and default
weights matching the GreenRAN paper/scenarios.
"""

from typing import List, Tuple
import numpy as np

# Re-use the core implementation from rslaq_action_spaces to avoid duplication
from .rslaq_action_spaces import (
    _softmax,
    build_discrete_action_table,
    continuous_action_to_prb,
    discrete_action_to_prb,
    scheduler_id_to_name,
)

# Default static weights from GreenRAN scenarios (greenran_normal)
DEFAULT_WEIGHTS = np.array([0.40, 0.15, 0.45], dtype=np.float32)

__all__ = [
    "build_discrete_action_table",
    "continuous_action_to_prb",
    "discrete_action_to_prb",
    "scheduler_id_to_name",
    "DEFAULT_WEIGHTS",
]
