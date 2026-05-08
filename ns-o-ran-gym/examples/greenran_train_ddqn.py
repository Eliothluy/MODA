"""
DDQN Training for GreenRAN (slice-aware-sim.cc).

Usage:
    python greenran_train_ddqn.py \
        --scenario greenran_normal \
        --episodes 35 \
        --simTime 2.0 \
        --ntsr 100 \
        --output results_greenran
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import argparse
import csv
import json
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque

from environments.greenran_env import GreenRanEnv
from environments.greenran_action_spaces import build_discrete_action_table

# Default paths
DEFAULT_NS3_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "ns-3-dev"
)
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "results_greenran")

SCENARIOS = [
    "greenran_low",
    "greenran_normal",
    "greenran_video_heavy",
    "greenran_congestion",
    "greenran_night_energy",
    "greenran_balanced",
]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# Build discrete action table (updated in train_ddqn based on args)
ACTION_TABLE = build_discrete_action_table(step=0.1, include_scheduler=True)
NUM_ACTIONS = len(ACTION_TABLE)


class QNetwork(nn.Module):
    """
    DNN architecture: four 2D convolutional layers, each followed by batch
    normalization, and a fully connected layer at the output.
    """

    def __init__(self, state_shape, action_size):
        super().__init__()
        h, w = state_shape

        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(32)
        self.conv3 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(64)
        self.conv4 = nn.Conv2d(64, 64, kernel_size=3, padding=1)
        self.bn4 = nn.BatchNorm2d(64)

        with torch.no_grad():
            x = torch.zeros(1, 1, h, w)
            x = torch.tanh(self.bn1(self.conv1(x)))
            x = torch.tanh(self.bn2(self.conv2(x)))
            x = torch.tanh(self.bn3(self.conv3(x)))
            x = torch.tanh(self.bn4(self.conv4(x)))
            flat = x.numel()

        self.fc = nn.Linear(flat, action_size)

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(0).unsqueeze(0)
        elif x.dim() == 3:
            x = x.unsqueeze(1)
        x = torch.tanh(self.bn1(self.conv1(x)))
        x = torch.tanh(self.bn2(self.conv2(x)))
        x = torch.tanh(self.bn3(self.conv3(x)))
        x = torch.tanh(self.bn4(self.conv4(x)))
        x = x.view(x.size(0), -1)
        return self.fc(x)


class DDQNAgent:
    def __init__(
        self,
        state_shape,
        action_size,
        lr=1e-3,
        gamma=0.80,
        epsilon=1.0,
        epsilon_min=0.05,
        epsilon_decay=0.998,
        buffer_size=128,
        batch_size=32,
        target_update=200,
    ):
        self.state_shape = state_shape
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        self.online_net = QNetwork(state_shape, action_size).to(device)
        self.target_net = QNetwork(state_shape, action_size).to(device)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.online_net.parameters(), lr=lr)
        self.memory = deque(maxlen=buffer_size)
        self.batch_size = batch_size
        self.target_update = target_update
        self.step_count = 0

    def act(self, state):
        if random.random() < self.epsilon:
            return random.randrange(self.action_size)
        self.online_net.eval()
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0).unsqueeze(0).to(device)
            q = self.online_net(s)
        self.online_net.train()
        return q.argmax(dim=1).item()

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state.copy(), action, reward, next_state.copy(), done))

    def replay(self):
        if len(self.memory) < self.batch_size:
            return None
        batch = random.sample(self.memory, self.batch_size)
        states = torch.FloatTensor(np.array([b[0] for b in batch])).to(device)
        actions = torch.LongTensor([b[1] for b in batch]).to(device)
        rewards = torch.FloatTensor([b[2] for b in batch]).to(device)
        next_states = torch.FloatTensor(np.array([b[3] for b in batch])).to(device)
        dones = torch.FloatTensor([b[4] for b in batch]).to(device)

        current_q = self.online_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            next_actions = self.online_net(next_states).argmax(dim=1)
            next_q = (
                self.target_net(next_states)
                .gather(1, next_actions.unsqueeze(1))
                .squeeze(1)
            )
            target_q = rewards + (1 - dones) * self.gamma * next_q

        loss = nn.MSELoss()(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), 1.0)
        self.optimizer.step()

        self.step_count += 1
        if self.step_count % self.target_update == 0:
            self.target_net.load_state_dict(self.online_net.state_dict())
        if self.epsilon > self.epsilon_min:
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        return loss.item()

    def save(self, path):
        torch.save(
            {
                "online": self.online_net.state_dict(),
                "target": self.target_net.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "epsilon": self.epsilon,
            },
            path,
        )

    def load(self, path):
        ckpt = torch.load(path, map_location=device, weights_only=False)
        self.online_net.load_state_dict(ckpt["online"])
        self.target_net.load_state_dict(ckpt["target"])
        self.optimizer.load_state_dict(ckpt["optimizer"])
        self.epsilon = ckpt.get("epsilon", 0.0)


def choose_scenario(episode, mode, scenarios_list):
    if mode == "random":
        return random.choice(scenarios_list)
    return scenarios_list[0]


def train_ddqn(args):
    set_seed(args.seed)

    os.makedirs(args.output, exist_ok=True)

    scenario_list = (
        args.scenarios.split(",")
        if args.scenarios
        else [args.scenario]
    )
    if args.scenario == "random":
        mode = "random"
        if not args.scenarios:
            scenario_list = SCENARIOS
    else:
        mode = "fixed"
        scenario_list = [args.scenario]

    global ACTION_TABLE, NUM_ACTIONS
    ACTION_TABLE = build_discrete_action_table(
        step=0.1, include_scheduler=args.include_scheduler
    )
    NUM_ACTIONS = len(ACTION_TABLE)
    print(f"Action table size: {NUM_ACTIONS} (include_scheduler={args.include_scheduler})")
    print(f"ntsr={args.ntsr}, total steps={args.episodes * args.ntsr}")

    if args.max_steps == "auto":
        max_steps = args.ntsr
    else:
        max_steps = int(args.max_steps)

    base_config = {}
    if args.config:
        with open(args.config, "r") as f:
            base_config = json.load(f)

    config = {
        "simTime": [args.simTime],
        "scenario": [scenario_list[0]],
        "seed": [args.seed],
        "seed_cycle": [args.seed_cycle],
        "periodMs": [args.periodMs],
    }
    # Merge JSON base config (CLI takes precedence for training-control params)
    for k, v in base_config.items():
        if k not in config:
            config[k] = v

    sla_config = {
        "max_buffer_bytes": args.max_buffer_bytes,
        "warmup_steps": args.warmup_steps,
        "consecutive_outage_steps": args.consecutive_outage_steps,
        "lambda_plr": args.lambda_plr,
    }

    env = GreenRanEnv(
        ns3_path=os.path.abspath(args.ns3_path),
        scenario_configuration=config,
        output_folder=args.output,
        optimized=False,
        action_mode=args.action_mode,
        observation_mode=args.observation_mode,
        max_steps=max_steps,
        apply_p_sta=args.apply_p_sta,
        include_scheduler=args.include_scheduler,
        sla_config=sla_config,
    )

    state_shape = env.observation_space.shape
    agent = DDQNAgent(
        state_shape,
        NUM_ACTIONS,
        lr=args.lr,
        gamma=args.gamma,
        epsilon=args.epsilon_start,
        epsilon_min=args.epsilon_min,
        epsilon_decay=args.epsilon_decay,
        buffer_size=args.buffer_size,
        batch_size=args.batch_size,
        target_update=args.target_update,
    )

    log_path = os.path.join(args.output, "greenran_ddqn_training_log.csv")
    with open(log_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "episode",
                "scenario",
                "total_reward",
                "avg_reward",
                "outage_count",
                "soft_count",
                "steps",
                "loss",
                "epsilon",
                "final_video_thr",
                "final_sensor_plr",
                "final_generic_thr",
                "action_video",
                "action_sensor",
                "action_generic",
            ]
        )

    best_avg = -float("inf")
    all_rewards = []
    avg100 = 0.0

    for ep in range(args.episodes):
        chosen_scenario = choose_scenario(ep, mode, scenario_list)
        env.scenario_configuration["scenario"] = [chosen_scenario]
        env.scenario_name = chosen_scenario

        obs, info = env.reset()
        state = obs.copy()
        ep_reward = 0.0
        ep_outages = 0
        ep_soft = 0
        ep_losses = []
        step = 0

        ep_max_steps = min(args.ntsr, env.max_steps)

        for step in range(ep_max_steps):
            action_idx = agent.act(state)
            next_obs, reward, terminated, truncated, info = env.step(action_idx)
            next_state = next_obs.copy()
            done = terminated or truncated

            agent.remember(state, action_idx, reward, next_state, float(done))
            loss = agent.replay()
            if loss is not None:
                ep_losses.append(loss)

            ep_reward += reward
            if info.get("outage_flags"):
                if any(info["outage_flags"].values()):
                    ep_outages += 1
            if info.get("soft_flags"):
                if any(info["soft_flags"].values()):
                    ep_soft += 1

            state = next_state
            if done:
                break

        all_rewards.append(ep_reward)
        avg100 = (
            np.mean(all_rewards[-100:])
            if len(all_rewards) >= 100
            else np.mean(all_rewards)
        )

        final_video_thr = info.get("slice_0_VIDEO_EMBB", {}).get("throughput_mbps", 0.0)
        final_sensor_plr = info.get("slice_1_SENSOR_MMTC", {}).get("plr_mean", 0.0)
        final_generic_thr = info.get("slice_2_GENERIC_EMBB", {}).get("throughput_mbps", 0.0)
        action_info = info.get("action_info", {})
        prb_pct = action_info.get("prb_pct", [0.0, 0.0, 0.0])

        with open(log_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    ep + 1,
                    chosen_scenario,
                    f"{ep_reward:.4f}",
                    f"{avg100:.4f}",
                    ep_outages,
                    ep_soft,
                    step + 1,
                    f"{np.mean(ep_losses):.6f}" if ep_losses else "",
                    f"{agent.epsilon:.4f}",
                    f"{final_video_thr:.4f}",
                    f"{final_sensor_plr:.4f}",
                    f"{final_generic_thr:.4f}",
                    f"{prb_pct[0]:.2f}",
                    f"{prb_pct[1]:.2f}",
                    f"{prb_pct[2]:.2f}",
                ]
            )

        if (ep + 1) % args.log_interval == 0:
            print(
                f"Ep {ep + 1}/{args.episodes} | Scenario: {chosen_scenario} | "
                f"Reward: {ep_reward:.4f} | Avg100: {avg100:.4f} | "
                f"Outages: {ep_outages} | Soft: {ep_soft} | Eps: {agent.epsilon:.4f}"
            )

        if avg100 > best_avg:
            best_avg = avg100
            agent.save(os.path.join(args.output, "greenran_ddqn_best.pt"))

    agent.save(os.path.join(args.output, "greenran_ddqn_final.pt"))

    summary = {
        "method": "ddqn",
        "scenario_mode": mode,
        "scenarios": scenario_list,
        "episodes": args.episodes,
        "ntsr": args.ntsr,
        "final_avg_100": float(avg100),
        "best_avg": float(best_avg),
    }
    with open(os.path.join(args.output, "greenran_ddqn_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    env.close()
    print(f"\nTraining complete. Best avg reward: {best_avg:.4f}")
    print(f"Logs saved to {log_path}")


def main():
    parser = argparse.ArgumentParser(description="DDQN Training for GreenRAN")
    parser.add_argument("--scenario", type=str, default="greenran_normal",
                        help="Scenario name or 'random'")
    parser.add_argument("--scenarios", type=str, default="",
                        help="Comma-separated list for random mode (default: all)")
    parser.add_argument("--config", type=str, default="",
                        help="Path to scenario configuration JSON file (e.g., greenran_use_case.json)")
    parser.add_argument("--ns3_path", type=str, default=DEFAULT_NS3_PATH)
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--seed_cycle", type=int, default=100)
    parser.add_argument("--episodes", type=int, default=35)
    parser.add_argument("--simTime", type=float, default=2.0)
    parser.add_argument("--periodMs", type=int, default=100)
    parser.add_argument("--ntsr", type=int, default=100,
                        help="Steps per episode before periodic reset")
    parser.add_argument("--max_steps", type=str, default="auto",
                        help="Max steps per episode or 'auto' (uses ntsr)")
    parser.add_argument("--observation_mode", type=str, default="paper")
    parser.add_argument("--action_mode", type=str, default="discrete")
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--gamma", type=float, default=0.80)
    parser.add_argument("--epsilon_start", type=float, default=1.0)
    parser.add_argument("--epsilon_min", type=float, default=0.05)
    parser.add_argument("--epsilon_decay", type=float, default=0.998)
    parser.add_argument("--buffer_size", type=int, default=128)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--target_update", type=int, default=200)
    parser.add_argument("--log_interval", type=int, default=1)
    parser.set_defaults(apply_p_sta=True)
    parser.add_argument("--no-apply-p-sta", action="store_false", dest="apply_p_sta",
                        help="Disable P_STA decomposition in Python (ns-3 handles it)")
    parser.set_defaults(include_scheduler=True)
    parser.add_argument("--no-include-scheduler", action="store_false", dest="include_scheduler",
                        help="Disable scheduler selection in action space")
    parser.add_argument("--max_buffer_bytes", type=float, default=100000.0)
    parser.add_argument("--warmup_steps", type=int, default=5)
    parser.add_argument("--consecutive_outage_steps", type=int, default=5)
    parser.add_argument("--lambda_plr", type=float, default=0.5,
                        help="PLR penalty weight in reward")
    args = parser.parse_args()

    if args.max_steps.lower() == "auto":
        args.max_steps = "auto"

    train_ddqn(args)


if __name__ == "__main__":
    main()
