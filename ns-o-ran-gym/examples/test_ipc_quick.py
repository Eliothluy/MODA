import sys

sys.path.insert(0, "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/src")

import json
import numpy as np
from environments.rslaq_env import RslaqEnv

NS3_PATH = "/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/"
OUTPUT = "/tmp/rslaq_test"

config = {
    "simTime": [4],
    "appStart": [0.5],
    "scenario": ["normal"],
    "seed": [1],
    "indicationPeriodicity": [10],
}

env = RslaqEnv(
    ns3_path=NS3_PATH,
    scenario_configuration=config,
    output_folder=OUTPUT,
    optimized=False,
)

print("Environment created. Calling reset()...")
obs, info = env.reset()
print(f"Initial obs shape: {obs.shape}")
print(f"Initial obs:\n{obs}")

heuristic_action = np.array(
    [
        [33.33, 20.0, 60.0],
        [33.33, 10.0, 40.0],
        [33.34, 5.0, 20.0],
    ]
)

for step in range(5):
    next_obs, reward, terminated, truncated, info = env.step(heuristic_action)
    print(
        f"\nStep {step + 1}: reward={reward:.4f}, term={terminated}, trunc={truncated}"
    )
    print(f"  obs:\n{next_obs}")
    if terminated or truncated:
        break

env.close()
print("\nTest complete!")
