#!/usr/bin/env python3
"""xApp Proof-of-Concept: O-RAN Slice Optimizer.

This script demonstrates how a trained offline DRL policy would function as an
xApp in an O-RAN architecture. It receives network-state KPMs (Key Performance
Metrics) and returns optimized slice allocation weights.

CONCEPTUAL O-RAN FLOW (not real E2/A1 integration):
  1. Near-RT RIC collects KPMs from gNB via E2 interface
  2. xApp receives KPMs as "network_state" (num UEs, offered load per slice)
  3. xApp runs inference: neural policy -> optimal weights [eMBB, URLLC, MTC]
  4. xApp sends weights back to RIC -> gNB scheduler via A1 policy

Usage:
    cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
    .venv-dashboard/bin/python examples/xapp_slice_optimizer.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

REPO_ROOT = Path("/home/elioth/Documentos/artigo_jussi")
MODELS_DIR = REPO_ROOT / "models"
DATA_ROOT = REPO_ROOT / "resultados_cenarios_finalizados_20260715"

STATE_COLS = [
    "num_ues_total", "num_ues_embb", "num_ues_urllc", "num_ues_mtc",
    "offered_load_embb", "offered_load_urllc", "offered_load_mtc",
    "pkt_size_embb", "pkt_size_urllc", "pkt_size_mtc",
    "is_low_traffic", "is_normal", "is_congestion", "is_stressed",
]
SLICE_NAMES = ["eMBB", "URLLC", "MTC"]
DEVICE = torch.device("cpu")


class QNet(nn.Module):
    def __init__(self, state_dim, n_actions):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128), nn.ReLU(),
            nn.Linear(128, 128), nn.ReLU(),
            nn.Linear(128, n_actions),
        )
    def forward(self, x):
        return self.net(x)


class ActorNet(nn.Module):
    def __init__(self, state_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128), nn.ReLU(),
            nn.Linear(128, 128), nn.ReLU(),
            nn.Linear(128, 3),
        )
    def forward(self, x):
        return F.softmax(self.net(x), dim=-1)


class SliceOptimizerXApp:
    """O-RAN xApp conceptual implementation for slice weight optimization.

    Trained offline from meta-heuristic optimization data, this xApp provides
    instant (<1ms) slice weight recommendations given the current network state.

    In a real O-RAN deployment, this would run as a container in the Near-RT RIC,
    receiving KPMs via E2 and pushing policies via A1.
    """

    def __init__(self, model_path: Path, model_type: str = "sac"):
        self.model_type = model_type
        ckpt = torch.load(model_path, map_location=DEVICE, weights_only=False)
        self.state_dim = ckpt["state_dim"]
        self.state_cols = ckpt.get("state_cols", STATE_COLS)

        if model_type == "ddqn":
            self.model = QNet(self.state_dim, ckpt["n_actions"])
            self.action_table = ckpt["action_table"]
        elif model_type == "sac":
            self.model = ActorNet(self.state_dim)
            self.action_table = None
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()

        # Load normalization params from dataset
        import pandas as pd
        df = pd.read_parquet(DATA_ROOT / "offline_dataset.parquet")
        state_df = df[STATE_COLS]
        self.norm_min = state_df.min().to_dict()
        self.norm_range = (state_df.max() - state_df.min()).replace(0, 1).to_dict()

    def _normalize_state(self, raw_state: dict) -> torch.Tensor:
        """Normalize raw KPM values to [0,1] using training-set statistics."""
        vals = []
        for col in STATE_COLS:
            v = raw_state.get(col, 0)
            v = (v - self.norm_min.get(col, 0)) / self.norm_range.get(col, 1)
            vals.append(max(0.0, min(1.0, v)))
        return torch.tensor(vals, dtype=torch.float32, device=DEVICE).unsqueeze(0)

    def predict_weights(self, network_state: dict) -> dict:
        """xApp entry point: receive KPMs, return optimal slice weights.

        Args:
            network_state: dict with keys like num_ues_total, offered_load_embb, etc.
                           Missing keys default to 0.

        Returns:
            dict with slice weights and metadata for the RIC policy.
        """
        x = self._normalize_state(network_state)
        with torch.no_grad():
            if self.model_type == "ddqn":
                q = self.model(x)
                idx = q.argmax(dim=1).item()
                weights = self.action_table[idx]
            else:  # sac
                weights = self.model(x).cpu().numpy()[0]

        # Ensure valid simplex
        weights = np.clip(weights, 0, None)
        weights = weights / weights.sum()

        return {
            "slice_weights": {
                "eMBB": float(weights[0]),
                "URLLC": float(weights[1]),
                "MTC": float(weights[2]),
            },
            "policy_type": "static_slice_weights",
            "model": f"offline_{self.model_type}",
            "inference_time_ms": "<1",
            "source": "trained_from_metaheuristic_data",
        }


def demo():
    """Demonstrate the xApp with all 4 scenarios."""
    print("=" * 75)
    print("  O-RAN xApp POC: Slice Optimizer (trained offline from meta-heuristics)")
    print("=" * 75)

    # Load SAC model (best performer in evaluation)
    model_path = MODELS_DIR / "sac_offline.pt"
    if not model_path.exists():
        print(f"Model not found: {model_path}")
        print("Run examples/train_offline_rl.py first.")
        return

    xapp = SliceOptimizerXApp(model_path, model_type="sac")
    print(f"\nLoaded model: {model_path.name} (SAC-offline)")
    print(f"Architecture: MLP(14 -> 128 -> 128 -> 3, softmax output)")
    print()

    # Define network states (simulating KPMs from E2 interface)
    test_states = [
        {
            "name": "Low Traffic (10 UEs, 57 Mbps offered)",
            "state": {
                "num_ues_total": 10, "num_ues_embb": 2, "num_ues_urllc": 2, "num_ues_mtc": 6,
                "offered_load_embb": 55.0, "offered_load_urllc": 1.0, "offered_load_mtc": 1.0,
                "pkt_size_embb": 1500, "pkt_size_urllc": 50, "pkt_size_mtc": 100,
                "is_low_traffic": 1, "is_normal": 0, "is_congestion": 0, "is_stressed": 0,
            },
        },
        {
            "name": "Normal (20 UEs, 73 Mbps offered)",
            "state": {
                "num_ues_total": 20, "num_ues_embb": 5, "num_ues_urllc": 5, "num_ues_mtc": 10,
                "offered_load_embb": 70.0, "offered_load_urllc": 1.0, "offered_load_mtc": 2.0,
                "pkt_size_embb": 1500, "pkt_size_urllc": 50, "pkt_size_mtc": 100,
                "is_low_traffic": 0, "is_normal": 1, "is_congestion": 0, "is_stressed": 0,
            },
        },
        {
            "name": "Congestion (60 UEs, 245 Mbps offered)",
            "state": {
                "num_ues_total": 60, "num_ues_embb": 15, "num_ues_urllc": 10, "num_ues_mtc": 35,
                "offered_load_embb": 180.0, "offered_load_urllc": 5.0, "offered_load_mtc": 60.0,
                "pkt_size_embb": 1500, "pkt_size_urllc": 100, "pkt_size_mtc": 500,
                "is_low_traffic": 0, "is_normal": 0, "is_congestion": 1, "is_stressed": 0,
            },
        },
        {
            "name": "Stressed (40 UEs, 128 Mbps offered)",
            "state": {
                "num_ues_total": 40, "num_ues_embb": 8, "num_ues_urllc": 12, "num_ues_mtc": 20,
                "offered_load_embb": 100.0, "offered_load_urllc": 3.0, "offered_load_mtc": 25.0,
                "pkt_size_embb": 1500, "pkt_size_urllc": 100, "pkt_size_mtc": 500,
                "is_low_traffic": 0, "is_normal": 0, "is_congestion": 0, "is_stressed": 1,
            },
        },
    ]

    for ts in test_states:
        print(f"\n--- {ts['name']} ---")
        result = xapp.predict_weights(ts["state"])
        w = result["slice_weights"]
        print(f"  Recommended weights:")
        print(f"    eMBB:  {w['eMBB']:.3f}  ({w['eMBB']*100:.1f}%)")
        print(f"    URLLC: {w['URLLC']:.3f}  ({w['URLLC']*100:.1f}%)")
        print(f"    MTC:   {w['MTC']:.3f}  ({w['MTC']*100:.1f}%)")
        print(f"  Inference time: {result['inference_time_ms']} ms")

    print("\n" + "=" * 75)
    print("  xApp Architecture (O-RAN conceptual):")
    print("=" * 75)
    print("""
  ┌─────────────────────────────────────────────────────────────┐
  │                    Near-RT RIC                              │
  │  ┌──────────────────────────────────────────────────────┐  │
  │  │  xApp: Slice Optimizer                               │  │
  │  │  ┌────────────┐    ┌──────────────┐    ┌──────────┐  │  │
  │  │  │ KPM Input  │───>│ Neural Policy│───>│ Weights  │  │  │
  │  │  │ (E2: UEs,  │    │ (SAC/DDQN,  │    │[eMBB,    │  │  │
  │  │  │  load/slice)│   │  trained    │    │ URLLC,   │  │  │
  │  │  │            │    │  offline)   │    │ MTC]     │  │  │
  │  │  └────────────┘    └──────────────┘    └────┬─────┘  │  │
  │  │                                            │A1      │  │
  │  └────────────────────────────────────────────┼────────┘  │
  └───────────────────────────────────────────────┼───────────┘
                                                   │
  ┌───────────────────────────────────────────────▼───────────┐
  │                    gNB Scheduler                           │
  │  slice_custom mode: floor(RBG_total × w_i) + remainder     │
  └────────────────────────────────────────────────────────────┘

  Training pipeline (offline):
  Meta-heuristics (GA/PSO/SA/Hybrid)  ──>  3600 candidate tuples
       ──>  Parquet dataset  ──>  Offline DRL training
       ──>  Neural policy (.pt)  ──>  xApp deployment
    """)


if __name__ == "__main__":
    demo()
