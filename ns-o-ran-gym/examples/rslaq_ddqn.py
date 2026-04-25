import argparse
import json
import numpy as np
import os
from collections import deque
import random
import torch
import torch.nn as nn
import torch.optim as optim
from environments.rslaq_env import RslaqEnv

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class QNetwork(nn.Module):
    def __init__(self, state_size, action_size, hidden_size=128):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)


class DDQNAgent:
    def __init__(
        self,
        state_size,
        action_size,
        learning_rate=0.001,
        gamma=0.99,
        epsilon=1.0,
        epsilon_min=0.01,
        epsilon_decay=0.995,
        buffer_size=10000,
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.learning_rate = learning_rate

        self.q_network = QNetwork(state_size, action_size).to(device)
        self.target_network = QNetwork(state_size, action_size).to(device)
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)

        self.memory = deque(maxlen=buffer_size)
        self.update_target_freq = 4
        self.train_step_counter = 0

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state, valid_actions=None):
        if np.random.rand() < self.epsilon:
            if valid_actions is not None:
                return random.choice(valid_actions)
            return random.randrange(self.action_size)

        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(device)
        with torch.no_grad():
            q_values = self.q_network(state_tensor).cpu().numpy()[0]

        if valid_actions is not None:
            masked_q = np.full(self.action_size, -np.inf)
            for a in valid_actions:
                masked_q[a] = q_values[a]
            return np.argmax(masked_q)

        return np.argmax(q_values)

    def replay(self, batch_size):
        if len(self.memory) < batch_size:
            return

        batch = random.sample(self.memory, batch_size)
        states = torch.FloatTensor(np.array([e[0] for e in batch])).to(device)
        actions = torch.LongTensor([e[1] for e in batch]).to(device)
        rewards = torch.FloatTensor([e[2] for e in batch]).to(device)
        next_states = torch.FloatTensor(np.array([e[3] for e in batch])).to(device)
        dones = torch.FloatTensor([e[4] for e in batch]).to(device)

        current_q = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            next_actions = self.q_network(next_states).argmax(1)
            next_q = (
                self.target_network(next_states)
                .gather(1, next_actions.unsqueeze(1))
                .squeeze(1)
            )
            target_q = rewards + (1 - dones) * self.gamma * next_q

        loss = nn.MSELoss()(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()

        self.train_step_counter += 1
        if self.train_step_counter % self.update_target_freq == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return loss.item()


def get_valid_actions():
    actions = []
    p_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    for p1 in p_values:
        for p2 in p_values:
            for p3 in p_values:
                if abs(p1 + p2 + p3 - 1.0) < 0.01:
                    action_idx = len(actions)
                    actions.append((p1, p2, p3))
                    if action_idx >= 66:
                        break
            else:
                continue
            break

    valid_indices = list(range(len(actions)))
    return valid_indices


def action_to_prb(action_idx, num_slices=3):
    p_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    combos = []
    for p1 in p_values:
        for p2 in p_values:
            for p3 in p_values:
                if abs(p1 + p2 + p3 - 1.0) < 0.01:
                    combos.append((p1, p2, p3))

    if action_idx >= len(combos):
        action_idx = action_idx % len(combos)

    p1, p2, p3 = combos[action_idx]

    action = np.array(
        [
            [p1 * 100, p1 * 100 * 0.5, p1 * 100],
            [p2 * 100, p2 * 100 * 0.5, p2 * 100],
            [p3 * 100, p3 * 100 * 0.5, p3 * 100],
        ]
    )
    return action


def train_ddqn(env, agent, num_episodes=100, batch_size=32, max_steps=50):
    scores = []
    avg_scores = deque(maxlen=100)

    print(f"Starting DDQN training for {num_episodes} episodes...")
    print(
        f"State size: {env.observation_space.shape}, Action size: {agent.action_size}"
    )

    for episode in range(num_episodes):
        obs, info = env.reset()
        state = obs.flatten()
        score = 0

        for step in range(max_steps):
            action_idx = agent.act(state)
            prb_action = action_to_prb(action_idx)

            next_obs, reward, terminated, truncated, info = env.step(prb_action)
            next_state = next_obs.flatten()
            done = terminated or truncated

            agent.remember(state, action_idx, reward, next_state, done)

            if len(agent.memory) >= batch_size:
                loss = agent.replay(batch_size)

            score += reward
            state = next_state

            if done:
                break

        scores.append(score)
        avg_scores.append(score)
        avg_score = np.mean(avg_scores)

        if (episode + 1) % 10 == 0:
            print(
                f"Episode {episode + 1}/{num_episodes} | Score: {score:.2f} | "
                f"Avg Score: {avg_score:.2f} | Epsilon: {agent.epsilon:.4f}"
            )

    print(f"\nTraining completed! Final avg score: {np.mean(avg_scores):.2f}")
    return scores


def evaluate(env, agent, num_episodes=5, max_steps=50):
    print("\n" + "=" * 60)
    print("EVALUATION PHASE")
    print("=" * 60)

    eval_scores = []

    for episode in range(num_episodes):
        obs, info = env.reset()
        state = obs.flatten()
        score = 0

        for step in range(max_steps):
            action_idx = agent.act(state)
            prb_action = action_to_prb(action_idx)

            next_obs, reward, terminated, truncated, info = env.step(prb_action)
            next_state = next_obs.flatten()
            done = terminated or truncated

            score += reward
            state = next_state

            if done:
                break

        eval_scores.append(score)
        print(f"Eval Episode {episode + 1}/{num_episodes} | Score: {score:.2f}")

    print(f"\nEvaluation completed! Avg Score: {np.mean(eval_scores):.2f}")
    return eval_scores


def run_scenario(env, agent, scenario_name, max_steps=50):
    env.scenario_configuration["scenario"] = [scenario_name]
    obs, info = env.reset()
    state = obs.flatten()
    score = 0
    rewards = []

    print(f"\n--- Scenario: {scenario_name} ---")

    for step in range(max_steps):
        action_idx = agent.act(state)
        prb_action = action_to_prb(action_idx)

        next_obs, reward, terminated, truncated, info = env.step(prb_action)
        next_state = next_obs.flatten()
        done = terminated or truncated

        score += reward
        rewards.append(reward)
        state = next_state

        if done:
            break

    avg_reward = np.mean(rewards) if rewards else 0
    print(
        f"Scenario {scenario_name}: Total Score = {score:.2f}, Avg Reward = {avg_reward:.4f}"
    )
    return score, avg_reward


def main():
    parser = argparse.ArgumentParser(description="DDQN Training for RSLAQ")
    parser.add_argument(
        "--config",
        type=str,
        default="/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/src/environments/scenario_configurations/rslaq_use_case.json",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--output_folder",
        type=str,
        default="ddqn_output",
        help="Output folder for results",
    )
    parser.add_argument(
        "--ns3_path",
        type=str,
        default="/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/",
        help="Path to NS-3 directory",
    )
    parser.add_argument(
        "--num_episodes", type=int, default=150, help="Number of training episodes"
    )
    parser.add_argument(
        "--batch_size", type=int, default=32, help="Batch size for replay"
    )
    parser.add_argument(
        "--max_steps", type=int, default=50, help="Max steps per episode"
    )
    parser.add_argument(
        "--optimized", action="store_true", help="Enable optimization mode"
    )
    parser.add_argument(
        "--model_path", type=str, default=None, help="Path to load pre-trained model"
    )

    args = parser.parse_args()

    with open(args.config) as f:
        params = json.load(f)

    scenario_configuration = params
    output_folder = args.output_folder
    ns3_path = args.ns3_path

    os.makedirs(output_folder, exist_ok=True)

    print("Creating RSLAQ Environment...")
    env = RslaqEnv(
        ns3_path=ns3_path,
        scenario_configuration=scenario_configuration,
        output_folder=output_folder,
        optimized=args.optimized,
    )

    state_size = env.observation_space.shape[0] * env.observation_space.shape[1]
    num_actions = 66

    print(f"State size: {state_size}, Action size: {num_actions}")

    agent = DDQNAgent(
        state_size=state_size,
        action_size=num_actions,
        learning_rate=0.001,
        gamma=0.99,
        epsilon=1.0,
        epsilon_min=0.01,
        epsilon_decay=0.995,
        buffer_size=10000,
    )

    if args.model_path and os.path.exists(args.model_path):
        print(f"Loading model from {args.model_path}")
        agent.q_network.load_state_dict(torch.load(args.model_path))
        agent.epsilon = 0.0

    scores = train_ddqn(env, agent, args.num_episodes, args.batch_size, args.max_steps)

    model_path = os.path.join(output_folder, "ddqn_model.pth")
    torch.save(agent.q_network.state_dict(), model_path)
    print(f"Model saved to {model_path}")

    results = {
        "training_scores": scores,
        "final_avg_score": float(np.mean(scores[-100:])),
        "epsilon_final": agent.epsilon,
    }

    with open(os.path.join(output_folder, "training_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    scenarios = [
        "low_traffic",
        "normal",
        "congestion",
        "stressed",
        "insufficient_resources",
    ]
    scenario_results = {}

    for scenario in scenarios:
        score, avg_reward = run_scenario(env, agent, scenario, args.max_steps)
        scenario_results[scenario] = {
            "total_score": float(score),
            "avg_reward": float(avg_reward),
        }

    with open(os.path.join(output_folder, "scenario_results.json"), "w") as f:
        json.dump(scenario_results, f, indent=2)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Training Episodes: {args.num_episodes}")
    print(f"Final Training Score: {np.mean(scores[-10:]):.2f}")
    print("\nScenario Results:")
    for scenario, res in scenario_results.items():
        print(
            f"  {scenario}: Score={res['total_score']:.2f}, Avg={res['avg_reward']:.4f}"
        )


if __name__ == "__main__":
    main()
