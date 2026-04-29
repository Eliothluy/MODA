import sys

sys.path.insert(0, "/home/elioth/Documentos/artigo_jussi/ns-o-ran-gym/src")

import argparse
import json
import os
import numpy as np

from environments.rslaq_env import RslaqEnv

NS3_PATH = "/home/elioth/Documentos/artigo_jussi/ns-3-dev/"
SCENARIOS = [
    "low_traffic",
    "normal",
    "congestion",
    "stressed",
    "insufficient_resources",
]

P_STA_WEIGHTS = np.array([0.33, 0.40, 0.27])
P_STA = P_STA_WEIGHTS * 0.5

OPT_P_OPT = {
    "low_traffic": np.array([0.10, 0.30, 0.10]),
    "normal": np.array([0.15, 0.25, 0.10]),
    "congestion": np.array([0.20, 0.20, 0.10]),
    "stressed": np.array([0.20, 0.20, 0.10]),
    "insufficient_resources": np.array([0.20, 0.25, 0.05]),
}

DEFAULT_WEIGHTS = np.array([0.3333, 0.4000, 0.2667], dtype=np.float64)

OPT_ACTIONS = {}
for scenario, p_opt in OPT_P_OPT.items():
    p_final = P_STA + p_opt
    # Invert continuous_action_to_prb to get the raw continuous action
    # that yields p_final after softmax + P_STA decomposition.
    target_softmax = 2.0 * p_final - DEFAULT_WEIGHTS
    target_softmax = np.clip(target_softmax, 1e-8, None)
    raw = np.log(target_softmax)
    raw = raw - raw.mean()
    OPT_ACTIONS[scenario] = raw.astype(np.float64)


def evaluate_scenario(scenario, output_dir, num_episodes=10, max_steps=50):
    scenario_dir = os.path.join(output_dir, scenario)
    os.makedirs(scenario_dir, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"OPT Baseline | Scenario: {scenario} | Episodes: {num_episodes}")
    print(f"{'=' * 60}")

    config = {
        "simTime": [4],
        "appStart": [0.5],
        "scenario": [scenario],
        "seed": [1],
        "periodMs": [10],
    }

    env = RslaqEnv(
        ns3_path=NS3_PATH,
        scenario_configuration=config,
        output_folder=scenario_dir,
        optimized=False,
    )

    fixed_action = OPT_ACTIONS[scenario]
    all_rewards = []
    all_step_rewards = []

    for ep in range(num_episodes):
        obs, info = env.reset()
        ep_reward = 0.0

        for step in range(max_steps):
            next_obs, reward, terminated, truncated, info = env.step(fixed_action)
            ep_reward += reward
            all_step_rewards.append(reward)

            if terminated or truncated:
                break

            obs = next_obs

        all_rewards.append(ep_reward)
        if (ep + 1) % 5 == 0:
            print(f"  Ep {ep + 1}/{num_episodes} | Reward: {ep_reward:.4f}")

    avg = np.mean(all_rewards)
    print(f"  Scenario {scenario}: Avg reward = {avg:.4f}")

    results = {
        "method": "opt",
        "scenario": scenario,
        "episodes": num_episodes,
        "rewards": all_rewards,
        "step_rewards": all_step_rewards,
        "avg_reward": float(avg),
        "std_reward": float(np.std(all_rewards)),
    }
    with open(os.path.join(scenario_dir, "opt_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    env.close()
    return results


def main():
    parser = argparse.ArgumentParser(description="OPT Baseline for RSLAQ with NS-3")
    parser.add_argument("--scenario", type=str, default="all")
    parser.add_argument(
        "--output",
        type=str,
        default="/home/elioth/Documentos/artigo_jussi/ns-o-ran-gym/results",
    )
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--max_steps", type=int, default=50)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    scenarios = SCENARIOS if args.scenario == "all" else [args.scenario]

    all_results = {}
    for scenario in scenarios:
        r = evaluate_scenario(scenario, args.output, args.episodes, args.max_steps)
        all_results[scenario] = r

    with open(os.path.join(args.output, "opt_all_results.json"), "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nAll OPT results saved to {args.output}")


if __name__ == "__main__":
    main()
