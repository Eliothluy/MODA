"""
RSLAQ Policy Evaluation.

Evaluates a trained SAC or DDQN checkpoint over N episodes and compares
against fixed baselines.

Usage:
    python rslaq_eval_policy.py \
        --algo sac \
        --checkpoint results/sac_best.pt \
        --scenario normal \
        --episodes 5 \
        --output results/eval
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import argparse
import csv
import json
import uuid
import random
import numpy as np
import torch

from environments.rslaq_env import RslaqEnv
from environments.rslaq_action_spaces import build_discrete_action_table

DEFAULT_NS3_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "ns-3-dev"
)
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "results", "eval")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class FixedBaselineAgent:
    """Agent that always returns a fixed PRB allocation."""

    def __init__(self, weights, action_mode="continuous"):
        self.weights = np.array(weights, dtype=np.float32)
        self.action_mode = action_mode

    def act(self, state):
        if self.action_mode == "continuous":
            # Return raw action that after softmax + P_STA yields the desired weights
            # This is approximate; for evaluation we directly send the PRB pct
            return self.weights
        else:
            # For discrete, just return index 0 (will be overridden by eval script)
            return 0


def load_sac_agent(checkpoint_path, state_shape):
    from examples.rslaq_train_sac import SACActor

    actor = SACActor(state_shape, action_dim=3).to(device)
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    actor.load_state_dict(ckpt["actor"])
    actor.eval()

    def act(state):
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0).unsqueeze(0).to(device)
            a, _ = actor.sample(s)
        return a.cpu().numpy().flatten()

    return act


def load_ddqn_agent(checkpoint_path, state_shape, action_size):
    from examples.rslaq_train_ddqn import QNetwork

    net = QNetwork(state_shape, action_size).to(device)
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    net.load_state_dict(ckpt["online"])
    net.eval()

    def act(state):
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0).unsqueeze(0).to(device)
            q = net(s)
        return q.argmax(dim=1).item()

    return act


def evaluate_agent(
    agent_fn,
    env_config,
    ns3_path,
    output_folder,
    episodes,
    action_mode,
    observation_mode,
    max_steps,
    run_id,
    agent_name,
):
    env = RslaqEnv(
        ns3_path=os.path.abspath(ns3_path),
        scenario_configuration=env_config.copy(),
        output_folder=output_folder,
        optimized=False,
        action_mode=action_mode,
        observation_mode=observation_mode,
        max_steps=max_steps if max_steps != "auto" else None,
        apply_p_sta=False,  # P_STA applied in Python, ns-3 receives final values
    )

    rows = []
    for ep in range(episodes):
        obs, info = env.reset()
        state = obs.copy()
        ep_reward = 0.0
        ep_outages = 0
        ep_soft = 0
        actions_log = []

        for step in range(env.max_steps):
            action = agent_fn(state)
            next_obs, reward, terminated, truncated, info = env.step(action)
            next_state = next_obs.copy()
            done = terminated or truncated

            ep_reward += reward
            actions_log.append(info.get("action_info", {}).get("prb_pct", [0, 0, 0]))

            if info.get("outage_flags"):
                if any(info["outage_flags"].values()):
                    ep_outages += 1
            if info.get("soft_flags"):
                if any(info["soft_flags"].values()):
                    ep_soft += 1

            state = next_state
            if done:
                break

        avg_action = np.mean(actions_log, axis=0) if actions_log else [0, 0, 0]
        final_embb = info.get("slice_0_eMBB", {}).get("throughput_mbps", 0.0)
        final_urllc = info.get("slice_1_URLLC", {}).get("plr_mean", 0.0)
        final_mtc = info.get("slice_2_MTC", {}).get("dLostPackets_sum", 0.0)

        rows.append(
            {
                "run_id": run_id,
                "agent": agent_name,
                "episode": ep + 1,
                "scenario": env.scenario_name,
                "total_reward": ep_reward,
                "steps": step + 1,
                "outages": ep_outages,
                "soft_violations": ep_soft,
                "final_embb_thr": final_embb,
                "final_urllc_plr": final_urllc,
                "final_mtc_lost": final_mtc,
                "avg_action_embb": avg_action[0],
                "avg_action_urllc": avg_action[1],
                "avg_action_mtc": avg_action[2],
            }
        )

    env.close()
    return rows


def main():
    parser = argparse.ArgumentParser(description="RSLAQ Policy Evaluation")
    parser.add_argument("--algo", type=str, required=True, choices=["sac", "ddqn"])
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--scenario", type=str, default="normal")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--eval_seeds", type=str, default="",
                        help="Comma-separated seeds for multi-seed evaluation (e.g., '1,2,3,4,5'). Overrides --seed if set.")
    parser.add_argument("--ns3_path", type=str, default=DEFAULT_NS3_PATH)
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT)
    parser.add_argument("--simTime", type=float, default=4.0)
    parser.add_argument("--appStart", type=float, default=0.5)
    parser.add_argument("--periodMs", type=int, default=10)
    parser.add_argument("--max_steps", type=str, default="auto")
    parser.add_argument("--observation_mode", type=str, default="paper")
    args = parser.parse_args()

    set_seed(args.seed)
    os.makedirs(args.output, exist_ok=True)
    run_id = str(uuid.uuid4())[:8]

    env_config = {
        "simTime": [args.simTime],
        "appStart": [args.appStart],
        "scenario": [args.scenario],
        "seed": [args.seed],
        "periodMs": [args.periodMs],
    }

    action_mode = "continuous" if args.algo == "sac" else "discrete"

    # Load agent
    if args.algo == "sac":
        # Need state_shape; create temporary env to get it
        tmp_env = RslaqEnv(
            ns3_path=os.path.abspath(args.ns3_path),
            scenario_configuration=env_config.copy(),
            output_folder=args.output,
            optimized=False,
            action_mode=action_mode,
            observation_mode=args.observation_mode,
            max_steps=1,
            apply_p_sta=False,
        )
        state_shape = tmp_env.observation_space.shape
        tmp_env.close()
        agent_fn = load_sac_agent(args.checkpoint, state_shape)
    else:
        tmp_env = RslaqEnv(
            ns3_path=os.path.abspath(args.ns3_path),
            scenario_configuration=env_config.copy(),
            output_folder=args.output,
            optimized=False,
            action_mode=action_mode,
            observation_mode=args.observation_mode,
            max_steps=1,
            apply_p_sta=False,
        )
        state_shape = tmp_env.observation_space.shape
        action_size = len(build_discrete_action_table(step=0.1, include_scheduler=False))
        tmp_env.close()
        agent_fn = load_ddqn_agent(args.checkpoint, state_shape, action_size)

    all_rows = []

    # Determine seeds for evaluation
    if args.eval_seeds:
        eval_seeds = [int(s.strip()) for s in args.eval_seeds.split(",")]
        print(f"Multi-seed evaluation with seeds: {eval_seeds}")
    else:
        eval_seeds = [args.seed]

    # Evaluate trained agent across all seeds
    for seed in eval_seeds:
        print(f"Evaluating {args.algo.upper()} on {args.scenario} (seed={seed}) ...")
        seed_config = env_config.copy()
        seed_config["seed"] = [seed]
        rows = evaluate_agent(
            agent_fn,
            seed_config,
            args.ns3_path,
            args.output,
            args.episodes,
            action_mode,
            args.observation_mode,
            args.max_steps,
            run_id,
            f"{args.algo}_s{seed}",
        )
        all_rows.extend(rows)

    # Baselines (only for continuous/resource mode)
    baselines = {
        "fixed_equal": [33.33, 33.33, 33.34],
        "embb_biased": [50.0, 30.0, 20.0],
        "urllc_biased": [20.0, 50.0, 30.0],
        "mtc_biased": [20.0, 30.0, 50.0],
    }

    for name, weights in baselines.items():
        print(f"Evaluating baseline {name} ...")
        baseline_agent = FixedBaselineAgent(weights, action_mode="continuous")
        for seed in eval_seeds:
            seed_config = env_config.copy()
            seed_config["seed"] = [seed]
            rows = evaluate_agent(
                baseline_agent.act,
                seed_config,
                args.ns3_path,
                args.output,
                args.episodes,
                "continuous",
                args.observation_mode,
                args.max_steps,
                run_id,
                f"{name}_s{seed}",
            )
            all_rows.extend(rows)

    # Save CSV
    csv_path = os.path.join(args.output, f"eval_{args.algo}_{args.scenario}_{run_id}.csv")
    if all_rows:
        keys = all_rows[0].keys()
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"Results saved to {csv_path}")

    summary = {
        "run_id": run_id,
        "algo": args.algo,
        "checkpoint": args.checkpoint,
        "scenario": args.scenario,
        "episodes": args.episodes,
        "seed": args.seed,
    }
    with open(os.path.join(args.output, f"eval_{run_id}_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
