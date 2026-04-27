import sys

sys.path.insert(0, "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/src")

import argparse
import json
import os
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


P_STA_WEIGHTS = np.array([0.33, 0.40, 0.27])
P_STA = P_STA_WEIGHTS * 0.5


class SACActor(nn.Module):
    """SAC Actor com entrada (3,5) e saída 3-dim contínua (pesos das slices)."""

    def __init__(self, state_shape, action_dim=3):
        super().__init__()
        h, w = state_shape
        self.conv1 = nn.Conv2d(1, 16, 2, padding=1)
        x = torch.zeros(1, 1, h, w)
        x = torch.relu(self.conv1(x))
        flat = x.numel()
        self.fc_mean = nn.Linear(flat, action_dim)
        self.fc_log_std = nn.Linear(flat, action_dim)

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(0).unsqueeze(0)
        elif x.dim() == 3:
            x = x.unsqueeze(1)
        x = torch.relu(self.conv1(x))
        x = x.view(x.size(0), -1)
        mean = self.fc_mean(x)
        log_std = self.fc_log_std(x)
        log_std = torch.clamp(log_std, -20, 2)
        return mean, log_std

    def sample(self, x):
        mean, log_std = self.forward(x)
        std = log_std.exp()
        normal = torch.distributions.Normal(mean, std)
        z = normal.rsample()
        action = torch.tanh(z)  # [-1, 1]
        log_prob = (
            normal.log_prob(z) - torch.log(1 - action.pow(2) + 1e-6)
        )
        log_prob = log_prob.sum(dim=-1, keepdim=True)
        return action, log_prob


class SACCritic(nn.Module):
    """SAC Critic: estima Q(s,a) concatenando estado e ação."""

    def __init__(self, state_shape, action_dim=3):
        super().__init__()
        h, w = state_shape
        self.conv1 = nn.Conv2d(1, 16, 2, padding=1)
        x = torch.zeros(1, 1, h, w)
        x = torch.relu(self.conv1(x))
        flat = x.numel()
        self.fc1 = nn.Linear(flat + action_dim, 128)
        self.fc2 = nn.Linear(128, 1)

    def forward(self, state, action):
        if state.dim() == 2:
            state = state.unsqueeze(0).unsqueeze(0)
        elif state.dim() == 3:
            state = state.unsqueeze(1)
        x = torch.relu(self.conv1(state))
        x = x.view(x.size(0), -1)
        x = torch.cat([x, action], dim=-1)
        x = torch.relu(self.fc1(x))
        return self.fc2(x)


class SACAgent:
    """Agente SAC com P_STA decomposition (50% estático + 50% dinâmico)."""

    def __init__(
        self,
        state_shape,
        action_dim=3,
        lr=1e-3,
        gamma=0.99,
        tau=0.005,
        alpha=0.1,
        buffer_size=10000,
        batch_size=256,
    ):
        self.gamma = gamma
        self.tau = tau
        self.alpha = alpha
        self.action_dim = action_dim

        self.actor = SACActor(state_shape, action_dim).to(device)
        self.critic1 = SACCritic(state_shape, action_dim).to(device)
        self.critic2 = SACCritic(state_shape, action_dim).to(device)
        self.critic1_target = SACCritic(state_shape, action_dim).to(device)
        self.critic2_target = SACCritic(state_shape, action_dim).to(device)
        self.critic1_target.load_state_dict(self.critic1.state_dict())
        self.critic2_target.load_state_dict(self.critic2.state_dict())

        self.actor_opt = optim.Adam(self.actor.parameters(), lr=lr)
        self.critic1_opt = optim.Adam(self.critic1.parameters(), lr=lr)
        self.critic2_opt = optim.Adam(self.critic2.parameters(), lr=lr)

        self.memory = deque(maxlen=buffer_size)
        self.batch_size = batch_size
        self.step_count = 0

    def continuous_to_prb(self, continuous_action):
        """
        Converte ação contínua [-1, 1] em PRB allocation via Softmax + P_STA.

        P_final = P_STA + softmax(action) * 0.5
        """
        a = continuous_action.cpu().numpy().flatten()

        # Softmax com estabilidade numérica
        exp_a = np.exp(a - np.max(a))
        p_opt = exp_a / exp_a.sum()
        p_opt *= 0.5  # agente controla 50%

        p_final = P_STA + p_opt
        p_final /= p_final.sum()  # renormalizar

        action = np.array(
            [
                [p_final[0] * 100.0, 0.0, 100.0],
                [p_final[1] * 100.0, 0.0, 100.0],
                [p_final[2] * 100.0, 0.0, 100.0],
            ],
            dtype=np.float64,
        )
        return action

    def act(self, state):
        s = torch.FloatTensor(state).unsqueeze(0).unsqueeze(0).to(device)
        with torch.no_grad():
            a, _ = self.actor.sample(s)
        return self.continuous_to_prb(a), a.cpu().numpy().flatten()

    def remember(self, state, action_cont, reward, next_state, done):
        self.memory.append(
            (state.copy(), action_cont.copy(), reward, next_state.copy(), done)
        )

    def replay(self):
        if len(self.memory) < self.batch_size:
            return None
        batch = random.sample(self.memory, self.batch_size)
        states = torch.FloatTensor(np.array([b[0] for b in batch])).to(device)
        actions = torch.FloatTensor(np.array([b[1] for b in batch])).to(device)
        rewards = torch.FloatTensor([b[2] for b in batch]).to(device)
        next_states = torch.FloatTensor(np.array([b[3] for b in batch])).to(device)
        dones = torch.FloatTensor([b[4] for b in batch]).to(device)

        with torch.no_grad():
            next_a, next_log_prob = self.actor.sample(next_states)
            q1_t = self.critic1_target(next_states, next_a)
            q2_t = self.critic2_target(next_states, next_a)
            q_t = torch.min(q1_t, q2_t) - self.alpha * next_log_prob
            q_backup = (
                rewards.unsqueeze(1) + (1 - dones.unsqueeze(1)) * self.gamma * q_t
            )

        q1 = self.critic1(states, actions)
        q2 = self.critic2(states, actions)
        c1_loss = nn.MSELoss()(q1, q_backup)
        c2_loss = nn.MSELoss()(q2, q_backup)

        self.critic1_opt.zero_grad()
        c1_loss.backward()
        self.critic1_opt.step()

        self.critic2_opt.zero_grad()
        c2_loss.backward()
        self.critic2_opt.step()

        a_new, log_prob_new = self.actor.sample(states)
        q1_pi = self.critic1(states, a_new)
        q2_pi = self.critic2(states, a_new)
        actor_loss = (self.alpha * log_prob_new - torch.min(q1_pi, q2_pi)).mean()

        self.actor_opt.zero_grad()
        actor_loss.backward()
        self.actor_opt.step()

        for p, tp in zip(self.critic1.parameters(), self.critic1_target.parameters()):
            tp.data.copy_(self.tau * p.data + (1 - self.tau) * tp.data)
        for p, tp in zip(self.critic2.parameters(), self.critic2_target.parameters()):
            tp.data.copy_(self.tau * p.data + (1 - self.tau) * tp.data)

        self.step_count += 1
        return c1_loss.item()

    def save(self, path):
        torch.save(
            {
                "actor": self.actor.state_dict(),
                "critic1": self.critic1.state_dict(),
                "critic2": self.critic2.state_dict(),
            },
            path,
        )

    def load(self, path):
        ckpt = torch.load(path, map_location=device, weights_only=False)
        self.actor.load_state_dict(ckpt["actor"])
        self.critic1.load_state_dict(ckpt["critic1"])
        self.critic2.load_state_dict(ckpt["critic2"])


def train_scenario(scenario, output_dir, num_episodes=50, max_steps=50):
    scenario_dir = os.path.join(output_dir, scenario)
    os.makedirs(scenario_dir, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"SAC Training | Scenario: {scenario} | Episodes: {num_episodes}")
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

    state_shape = env.observation_space.shape
    agent = SACAgent(
        state_shape,
        action_dim=3,  # 3 pesos contínuos (eMBB, URLLC, MTC)
        lr=1e-3,
        gamma=0.99,
        tau=0.005,
        alpha=0.1,
        buffer_size=10000,
        batch_size=256,
    )

    all_rewards = []
    best_avg = -float("inf")

    for ep in range(num_episodes):
        obs, info = env.reset()
        state = obs.copy()
        ep_reward = 0.0

        for step in range(max_steps):
            prb_action, action_cont = agent.act(state)
            # Enviar ação contínua (3 valores) para o env; o env faz pós-processamento
            next_obs, reward, terminated, truncated, info = env.step(action_cont)
            next_state = next_obs.copy()
            done = terminated or truncated

            agent.remember(state, action_cont, reward, next_state, float(done))
            agent.replay()

            ep_reward += reward
            state = next_state

            if done:
                break

        all_rewards.append(ep_reward)
        avg100 = np.mean(all_rewards[-100:])

        if (ep + 1) % 5 == 0:
            print(
                f"  Ep {ep + 1}/{num_episodes} | Reward: {ep_reward:.4f} | Avg100: {avg100:.4f}"
            )

        if avg100 > best_avg:
            best_avg = avg100
            agent.save(os.path.join(scenario_dir, "sac_best.pth"))

    agent.save(os.path.join(scenario_dir, "sac_final.pth"))

    results = {
        "method": "sac",
        "scenario": scenario,
        "episodes": num_episodes,
        "rewards": all_rewards,
        "final_avg_100": float(np.mean(all_rewards[-100:])),
        "best_avg": float(best_avg),
    }
    with open(os.path.join(scenario_dir, "sac_training.json"), "w") as f:
        json.dump(results, f, indent=2)

    env.close()
    print(f"  Scenario {scenario} done. Best avg: {best_avg:.4f}")
    return results


def main():
    parser = argparse.ArgumentParser(description="SAC Training for RSLAQ with NS-3")
    parser.add_argument("--scenario", type=str, default="all")
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

    with open(os.path.join(args.output, "sac_all_results.json"), "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nAll SAC results saved to {args.output}")


if __name__ == "__main__":
    main()
