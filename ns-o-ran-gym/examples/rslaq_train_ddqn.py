import sys

sys.path.insert(0, "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/src")

import argparse
import json
import os
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random

from environments.rslaq_env import RslaqEnv

NS3_PATH = "/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/"
SCENARIOS = [
    "low_traffic",
    "normal",
    "congestion",
    "stressed",
    "insufficient_resources",
]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def build_action_table():
    p_values = [round(x * 0.1, 1) for x in range(11)]
    sch_values = [0, 1, 2]
    combos = []
    for p1 in p_values:
        for p2 in p_values:
            for p3 in p_values:
                for sch in sch_values:
                    if abs(p1 + p2 + p3 - 1.0) < 0.01:
                        combos.append((p1, p2, p3, sch))
    return combos


ACTION_TABLE = build_action_table()
NUM_ACTIONS = len(ACTION_TABLE)


P_STA_WEIGHTS = np.array([0.33, 0.40, 0.27])
P_STA = P_STA_WEIGHTS * 0.5


def action_to_prb(action_idx):
    p1, p2, p3, sch = ACTION_TABLE[action_idx % len(ACTION_TABLE)]
    p_opt = np.array([p1, p2, p3]) * 0.5
    p_final = P_STA + p_opt
    action = np.array(
        [
            [p_final[0] * 100.0, 0.0, 100.0],
            [p_final[1] * 100.0, 0.0, 100.0],
            [p_final[2] * 100.0, 0.0, 100.0],
        ],
        dtype=np.float64,
    )
    return action, sch


class ConvQNetwork(nn.Module):
    def __init__(self, state_shape, action_size):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=2, padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=2, padding=1)
        self.bn2 = nn.BatchNorm2d(32)
        self.conv3 = nn.Conv2d(32, 64, kernel_size=2, padding=1)
        self.bn3 = nn.BatchNorm2d(64)
        self.conv4 = nn.Conv2d(64, 64, kernel_size=2, padding=0)
        self.bn4 = nn.BatchNorm2d(64)

        x = torch.zeros(1, 1, state_shape[0], state_shape[1])
        x = torch.tanh(self.bn1(self.conv1(x)))
        x = torch.tanh(self.bn2(self.conv2(x)))
        x = torch.tanh(self.bn3(self.conv3(x)))
        x = torch.tanh(self.bn4(self.conv4(x)))
        fc_size = x.numel()

        self.fc = nn.Linear(fc_size, action_size)

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
        lr=0.001,
        gamma=0.80,
        epsilon=1.0,
        epsilon_min=0.05,
        epsilon_lambda=0.998,
        buffer_size=500,
        batch_size=350,
        target_update=200,
    ):
        self.state_shape = state_shape
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_lambda = epsilon_lambda

        self.online_net = ConvQNetwork(state_shape, action_size).to(device)
        self.target_net = ConvQNetwork(state_shape, action_size).to(device)
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
        s = torch.FloatTensor(state).unsqueeze(0).unsqueeze(0).to(device)
        with torch.no_grad():
            q = self.online_net(s)
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
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_lambda)
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


def train_scenario(scenario, output_dir, num_episodes=50, max_steps=50):
    scenario_dir = os.path.join(output_dir, scenario)
    os.makedirs(scenario_dir, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"DDQN Training | Scenario: {scenario} | Episodes: {num_episodes}")
    print(f"{'=' * 60}")

    config = {
        "simTime": [4],
        "appStart": [0.5],
        "scenario": [scenario],
        "seed": [1],
        "indicationPeriodicity": [10],
    }

    env = RslaqEnv(
        ns3_path=NS3_PATH,
        scenario_configuration=config,
        output_folder=scenario_dir,
        optimized=False,
    )

    state_shape = env.observation_space.shape
    agent = DDQNAgent(
        state_shape,
        NUM_ACTIONS,
        lr=0.001,
        gamma=0.80,
        epsilon=1.0,
        epsilon_min=0.05,
        epsilon_lambda=0.998,
        buffer_size=500,
        batch_size=350,
        target_update=200,
    )

    all_rewards = []
    best_avg = -float("inf")

    for ep in range(num_episodes):
        obs, info = env.reset()
        state = obs.copy()
        ep_reward = 0.0

        for step in range(max_steps):
            action_idx = agent.act(state)
            prb_action, _ = action_to_prb(action_idx)  # scheduler sch ignorado (ns-3 não suporta)
            next_obs, reward, terminated, truncated, info = env.step(prb_action)
            next_state = next_obs.copy()
            done = terminated or truncated

            agent.remember(state, action_idx, reward, next_state, float(done))
            agent.replay()

            ep_reward += reward
            state = next_state

            if done:
                break

        all_rewards.append(ep_reward)
        avg100 = np.mean(all_rewards[-100:])

        if (ep + 1) % 5 == 0:
            print(
                f"  Ep {ep + 1}/{num_episodes} | Reward: {ep_reward:.4f} | "
                f"Avg100: {avg100:.4f} | Eps: {agent.epsilon:.4f}"
            )

        if avg100 > best_avg:
            best_avg = avg100
            agent.save(os.path.join(scenario_dir, "ddqn_best.pth"))

    agent.save(os.path.join(scenario_dir, "ddqn_final.pth"))

    results = {
        "method": "ddqn",
        "scenario": scenario,
        "episodes": num_episodes,
        "rewards": all_rewards,
        "final_avg_100": float(np.mean(all_rewards[-100:])),
        "best_avg": float(best_avg),
    }
    with open(os.path.join(scenario_dir, "ddqn_training.json"), "w") as f:
        json.dump(results, f, indent=2)

    env.close()
    print(f"  Scenario {scenario} done. Best avg: {best_avg:.4f}")
    return results


def main():
    parser = argparse.ArgumentParser(description="DDQN Training for RSLAQ with NS-3")
    parser.add_argument(
        "--scenario", type=str, default="all", help="Scenario name or 'all'"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results",
    )
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--max_steps", type=int, default=50)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    scenarios = SCENARIOS if args.scenario == "all" else [args.scenario]

    all_results = {}
    for scenario in scenarios:
        r = train_scenario(scenario, args.output, args.episodes, args.max_steps)
        all_results[scenario] = r

    with open(os.path.join(args.output, "ddqn_all_results.json"), "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nAll DDQN results saved to {args.output}")


if __name__ == "__main__":
    main()
