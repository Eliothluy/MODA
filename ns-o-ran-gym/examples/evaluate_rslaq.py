#!/usr/bin/env python3
"""
RSLAQ Evaluation Script
Runs trained DDQN agent and generates metrics for comparison with baselines.
"""

import sys
sys.path.insert(0, "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/src")

import argparse
import json
import os
import numpy as np
import torch
from collections import defaultdict

from environments.rslaq_env import RslaqEnv, ACTION_TABLE, action_to_prb

NS3_PATH = "/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/"
SCENARIOS = ["low_traffic", "normal", "congestion", "stressed", "insufficient_resources"]


def load_agent(model_path, state_shape, action_size):
    """Load trained DDQN agent."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    from rslaq_train_ddqn import ConvQNetwork, DDQNAgent
    
    agent = DDQNAgent(
        state_shape,
        action_size,
        lr=0.001,
        gamma=0.80,
        epsilon=0.0,
        epsilon_min=0.05,
        epsilon_lambda=0.998,
        buffer_size=500,
        batch_size=350,
        target_update=200,
    )
    agent.online_net.load_state_dict(torch.load(model_path, map_location=device)["online"])
    agent.online_net.eval()
    return agent


def evaluate_scenario(scenario, model_path, num_runs=5, max_steps=100):
    """Evaluate agent on a scenario."""
    results = {
        "throughput": defaultdict(list),
        "delay": defaultdict(list),
        "pdr": defaultdict(list),
        "plr": defaultdict(list),
    }
    
    for run in range(num_runs):
        config = {
            "simTime": [4],
            "appStart": [0.5],
            "scenario": [scenario],
            "seed": [run + 1],
            "indicationPeriodicity": [10],
        }
        
        env = RslaqEnv(
            ns3_path=NS3_PATH,
            scenario_configuration=config,
            output_folder=f"/tmp/rslaq_eval_{scenario}_{run}",
            optimized=False,
        )
        
        obs, info = env.reset()
        state = obs.copy()
        
        for step in range(max_steps):
            action_idx = agent.act(state)
            prb_action, _ = action_to_prb(action_idx)
            next_obs, reward, terminated, truncated, info = env.step(prb_action)
            state = next_obs.copy()
            
            if terminated or truncated:
                break
        
        env.close()
    
    return results


def run_baseline(scenario, scheduler_type, num_runs=3, sim_time=4):
    """Run a baseline (RR, PF, BCQI) by fixing scheduler type."""
    print(f"  Running {scheduler_type} baseline...")
    results = {}
    
    for run in range(num_runs):
        output_dir = f"/tmp/rslaq_baseline_{scheduler_type}_{run}"
        
        config = {
            "simTime": [sim_time],
            "appStart": [0.5],
            "scenario": [scenario],
            "seed": [run + 1],
        }
        
        env = RslaqEnv(
            ns3_path=NS3_PATH,
            scenario_configuration=config,
            output_folder=output_dir,
        )
        
        obs, info = env.reset()
        
        fixed_action = np.array([
            [33.3, 0.0, 100.0],
            [33.3, 0.0, 100.0],
            [33.4, 0.0, 100.0],
        ])
        
        for step in range(50):
            obs, reward, done, _, info = env.step(fixed_action)
            if done:
                break
        
        env.close()
    
    return results


def main():
    parser = argparse.ArgumentParser(description="RSLAQ Evaluation")
    parser.add_argument("--model", type=str, required=True, help="Path to trained model .pth")
    parser.add_argument("--scenario", type=str, default="all", help="Scenario or 'all'")
    parser.add_argument("--runs", type=int, default=5, help="Number of evaluation runs")
    parser.add_argument("--output", type=str, default="/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results/eval")
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
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
        output_folder="/tmp/rslaq_eval_init",
    )
    state_shape = env.observation_space.shape
    NUM_ACTIONS = len(ACTION_TABLE)
    env.close()
    
    print(f"Loading model from {args.model}")
    agent = load_agent(args.model, state_shape, NUM_ACTIONS)
    
    scenarios = SCENARIOS if args.scenario == "all" else [args.scenario]
    
    all_results = {}
    for scenario in scenarios:
        print(f"\n=== Evaluating {scenario} ===")
        results = evaluate_scenario(scenario, args.model, args.runs)
        all_results[scenario] = results
    
    output_file = os.path.join(args.output, f"eval_{os.path.basename(args.model)}.json")
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()