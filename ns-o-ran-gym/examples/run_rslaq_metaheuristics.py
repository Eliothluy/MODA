#!/usr/bin/env python3
"""Offline meta-heuristic search for RSLAQ slice_custom PRB weights.

This runner keeps the ns-3 baselines intact and uses repeated network-only
simulations to optimize the slice PRB vector [eMBB, URLLC, MTC]. GA, PSO, SA
and the hybrid method operate only on the weight simplex; the ns-3 scheduler
still applies the selected intra-slice algorithm through the existing
slice_custom mode.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence


SLICE_NAMES = ("eMBB", "URLLC", "MTC")


@dataclass
class Evaluation:
    method: str
    evaluation_id: int
    scenario: str
    seed: int
    run: int
    weights: list[float]
    score: float
    result_dir: Path
    log_file: Path


@dataclass
class Particle:
    position: list[float]
    velocity: list[float]
    personal_best: list[float]
    personal_score: float = -math.inf


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, "", "NA"):
            return default
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return min(max(value, lo), hi)


def normalize_weights(values: Sequence[float]) -> list[float]:
    clean = [max(float(v), 0.0) for v in values[:3]]
    if len(clean) < 3:
        clean.extend([0.0] * (3 - len(clean)))
    total = sum(clean)
    if total <= 0.0:
        return [1.0 / 3.0] * 3
    return [v / total for v in clean]


def format_weights(weights: Sequence[float]) -> str:
    normalized = normalize_weights(weights)
    first = round(normalized[0], 6)
    second = round(normalized[1], 6)
    third = round(1.0 - first - second, 6)
    if third < 0.0:
        rounded = normalize_weights([first, second, max(third, 0.0)])
    else:
        rounded = [first, second, third]
    return ",".join(f"{weight:.6f}" for weight in rounded)


def build_sim_command(
    *,
    scenario: str,
    output_root: Path,
    weights: Sequence[float],
    intra_algo: str,
    sim_time: float,
    app_start: float,
    drain_time: float,
    period_ms: int,
    seed: int,
    run: int,
    tx_power: float = 43.0,
    tdd_pattern: str = "D|D|8D|4GB|4U|U|U",
    rlc_mode: str = "um",
) -> str:
    return (
        "scratch/rslaq/rslaq-sim "
        f"--scenario={scenario} "
        "--baselineMode=slice_custom "
        f"--weights={format_weights(weights)} "
        f"--intraAlgo={intra_algo} "
        f"--simTime={sim_time:g} "
        f"--appStart={app_start:g} "
        f"--drainTimeSec={drain_time:g} "
        f"--periodMs={period_ms} "
        f"--seed={seed} "
        f"--run={run} "
        f"--txPower={tx_power:g} "
        f"--tddPattern={tdd_pattern} "
        f"--rlcMode={rlc_mode} "
        f"--outputDir={output_root}"
    )


def read_summary(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as handle:
        return list(csv.DictReader(handle))


def score_summary_rows(rows: Iterable[dict[str, str]]) -> float:
    by_slice = {row.get("slice", ""): row for row in rows}
    if not all(name in by_slice for name in SLICE_NAMES):
        return -1e9

    sla = []
    offered = []
    pdr = []
    util = []
    for name in SLICE_NAMES:
        row = by_slice[name]
        sla.append(clamp(safe_float(row.get("sla_satisfaction_pct")) / 100.0))
        offered.append(clamp(safe_float(row.get("offered_load_satisfaction_pct")) / 100.0))
        pdr.append(clamp(safe_float(row.get("pdr_pct")) / 100.0))
        util_value = safe_float(row.get("budget_utilization_pct_mean"), 50.0)
        util.append(clamp(util_value / 100.0))

    mean_sla = sum(sla) / len(sla)
    min_sla = min(sla)
    mean_offered = sum(offered) / len(offered)
    mean_pdr = sum(pdr) / len(pdr)
    mean_util = sum(util) / len(util)

    urllc = by_slice["URLLC"]
    mtc = by_slice["MTC"]
    embb = by_slice["eMBB"]

    urllc_delay_ms = safe_float(urllc.get("delay_ms_mean"))
    urllc_delay_penalty = clamp((urllc_delay_ms - 10.0) / 200.0)

    mtc_thr = safe_float(mtc.get("throughput_mbps_mean"))
    mtc_starvation_penalty = max(0.0, 1.0 - sla[2])
    if mtc_thr <= 1e-9:
        mtc_starvation_penalty += 0.5

    embb_buffer = safe_float(embb.get("buffer_bytes_mean"))
    embb_buffer_penalty = 0.05 * clamp(embb_buffer / 5_000_000.0)

    score = 100.0 * (
        0.35 * mean_sla
        + 0.20 * min_sla
        + 0.20 * mean_offered
        + 0.15 * mean_pdr
        + 0.10 * mean_util
    )
    score -= 25.0 * urllc_delay_penalty
    score -= 40.0 * mtc_starvation_penalty
    score -= 100.0 * embb_buffer_penalty
    return score


def random_weights(rng: random.Random) -> list[float]:
    return normalize_weights([rng.random(), rng.random(), rng.random()])


def mutate_weights(weights: Sequence[float], rng: random.Random, strength: float) -> list[float]:
    return normalize_weights([w + rng.gauss(0.0, strength) for w in weights])


def crossover_weights(a: Sequence[float], b: Sequence[float], rng: random.Random) -> list[float]:
    alpha = rng.random()
    return normalize_weights([alpha * x + (1.0 - alpha) * y for x, y in zip(a, b)])


def seed_weight_candidates(rng: random.Random, population_size: int) -> list[list[float]]:
    priors = [
        [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0],
        [0.3333, 0.4000, 0.2667],
        [0.70, 0.05, 0.25],
        [0.60, 0.15, 0.25],
        [0.55, 0.25, 0.20],
        [0.45, 0.35, 0.20],
        [0.50, 0.10, 0.40],
        [0.25, 0.45, 0.30],
    ]
    candidates: list[list[float]] = []
    seen: set[tuple[float, float, float]] = set()
    for candidate in priors:
        normalized = normalize_weights(candidate)
        key = tuple(round(value, 6) for value in normalized)
        if key not in seen:
            candidates.append(normalized)
            seen.add(key)
        if len(candidates) >= population_size:
            return candidates

    while len(candidates) < population_size:
        candidates.append(random_weights(rng))
    return candidates


def summary_path(output_root: Path, scenario: str, seed: int, run: int) -> Path:
    return (
        output_root
        / "results_rslaq_network_only"
        / f"scenario={scenario}"
        / "mode=slice_custom"
        / f"seed={seed}_run={run}"
        / "summary.csv"
    )


def result_dir(output_root: Path, scenario: str, seed: int, run: int) -> Path:
    return summary_path(output_root, scenario, seed, run).parent


def run_candidate(
    *,
    ns3_dir: Path,
    eval_root: Path,
    method: str,
    evaluation_id: int,
    scenario: str,
    weights: Sequence[float],
    intra_algo: str,
    sim_time: float,
    app_start: float,
    drain_time: float,
    period_ms: int,
    seed: int,
    run: int,
    tx_power: float,
    tdd_pattern: str,
    rlc_mode: str,
) -> Evaluation:
    candidate_root = eval_root / f"{method}_eval_{evaluation_id:04d}"
    candidate_root.mkdir(parents=True, exist_ok=True)
    log_file = candidate_root / "ns3.log"
    command = build_sim_command(
        scenario=scenario,
        output_root=candidate_root,
        weights=weights,
        intra_algo=intra_algo,
        sim_time=sim_time,
        app_start=app_start,
        drain_time=drain_time,
        period_ms=period_ms,
        seed=seed,
        run=run,
        tx_power=tx_power,
        tdd_pattern=tdd_pattern,
        rlc_mode=rlc_mode,
    )

    with log_file.open("w") as log:
        completed = subprocess.run(
            ["./ns3", "run", command],
            cwd=ns3_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError(f"ns-3 run failed for {method} eval {evaluation_id}; see {log_file}")

    out_summary = summary_path(candidate_root, scenario, seed, run)
    if not out_summary.exists():
        raise RuntimeError(f"summary.csv missing after {method} eval {evaluation_id}: {out_summary}")

    rows = read_summary(out_summary)
    return Evaluation(
        method=method,
        evaluation_id=evaluation_id,
        scenario=scenario,
        seed=seed,
        run=run,
        weights=normalize_weights(weights),
        score=score_summary_rows(rows),
        result_dir=result_dir(candidate_root, scenario, seed, run),
        log_file=log_file,
    )


def optimize_ga(
    rng: random.Random,
    evaluate: Callable[[str, int, Sequence[float]], Evaluation],
    iterations: int,
    population_size: int,
    mutation_strength: float,
) -> list[Evaluation]:
    population = [random_weights(rng) for _ in range(population_size)]
    evaluations: list[Evaluation] = []
    eval_id = 0

    for _ in range(iterations):
        generation: list[Evaluation] = []
        for weights in population:
            eval_id += 1
            result = evaluate("ga", eval_id, weights)
            generation.append(result)
            evaluations.append(result)

        generation.sort(key=lambda item: item.score, reverse=True)
        elite_count = max(2, population_size // 3)
        elites = [item.weights for item in generation[:elite_count]]
        next_population = list(elites)
        while len(next_population) < population_size:
            parent_a, parent_b = rng.sample(elites, 2)
            child = crossover_weights(parent_a, parent_b, rng)
            child = mutate_weights(child, rng, mutation_strength)
            next_population.append(child)
        population = next_population

    return evaluations


def optimize_pso(
    rng: random.Random,
    evaluate: Callable[[str, int, Sequence[float]], Evaluation],
    iterations: int,
    particles: int,
) -> list[Evaluation]:
    positions = [random_weights(rng) for _ in range(particles)]
    velocities = [[0.0, 0.0, 0.0] for _ in range(particles)]
    personal_best = [list(pos) for pos in positions]
    personal_scores = [-math.inf] * particles
    global_best = [1.0 / 3.0] * 3
    global_score = -math.inf
    evaluations: list[Evaluation] = []
    eval_id = 0

    for _ in range(iterations):
        for i, position in enumerate(positions):
            eval_id += 1
            result = evaluate("pso", eval_id, position)
            evaluations.append(result)
            if result.score > personal_scores[i]:
                personal_scores[i] = result.score
                personal_best[i] = list(result.weights)
            if result.score > global_score:
                global_score = result.score
                global_best = list(result.weights)

        for i in range(particles):
            for d in range(3):
                r1 = rng.random()
                r2 = rng.random()
                velocities[i][d] = (
                    0.55 * velocities[i][d]
                    + 1.30 * r1 * (personal_best[i][d] - positions[i][d])
                    + 1.30 * r2 * (global_best[d] - positions[i][d])
                )
            positions[i] = normalize_weights([positions[i][d] + velocities[i][d] for d in range(3)])

    return evaluations


def optimize_sa(
    rng: random.Random,
    evaluate: Callable[[str, int, Sequence[float]], Evaluation],
    iterations: int,
    mutation_strength: float,
) -> list[Evaluation]:
    current = [1.0 / 3.0] * 3
    evaluations: list[Evaluation] = []
    current_result: Evaluation | None = None

    for eval_id in range(1, iterations + 1):
        temperature = max(0.01, 1.0 - (eval_id - 1) / max(iterations, 1))
        candidate = mutate_weights(current, rng, mutation_strength * temperature)
        candidate_result = evaluate("sa", eval_id, candidate)
        evaluations.append(candidate_result)

        if current_result is None:
            current = list(candidate_result.weights)
            current_result = candidate_result
            continue

        delta = candidate_result.score - current_result.score
        if delta >= 0.0 or rng.random() < math.exp(delta / max(temperature * 20.0, 1e-9)):
            current = list(candidate_result.weights)
            current_result = candidate_result

    return evaluations


def optimize_hybrid(
    rng: random.Random,
    evaluate: Callable[[str, int, Sequence[float]], Evaluation],
    iterations: int,
    population_size: int,
    mutation_strength: float,
) -> list[Evaluation]:
    population_size = max(1, population_size)
    particles = [
        Particle(position=list(weights), velocity=[0.0, 0.0, 0.0], personal_best=list(weights))
        for weights in seed_weight_candidates(rng, population_size)
    ]
    global_best = [1.0 / 3.0] * 3
    global_score = -math.inf
    current_result: Evaluation | None = None
    archive: list[Evaluation] = []
    evaluations: list[Evaluation] = []
    eval_id = 0
    stagnant_iterations = 0

    for iteration in range(iterations):
        temperature = max(0.05, 1.0 - iteration / max(iterations, 1))
        generation: list[Evaluation] = []
        improved = False

        for particle in particles:
            eval_id += 1
            result = evaluate("hybrid", eval_id, particle.position)
            evaluations.append(result)
            generation.append(result)
            if result.score > particle.personal_score:
                particle.personal_score = result.score
                particle.personal_best = list(result.weights)
            if result.score > global_score:
                global_score = result.score
                global_best = list(result.weights)
                improved = True

        archive = sorted(archive + generation, key=lambda item: item.score, reverse=True)[: max(2, population_size)]
        if archive and current_result is None:
            current_result = archive[0]
        stagnant_iterations = 0 if improved else stagnant_iterations + 1

        adaptive_mutation = mutation_strength * (1.0 + 0.5 * min(stagnant_iterations, 3))
        eval_id += 1
        local_candidate = mutate_weights(global_best, rng, adaptive_mutation * temperature)
        local_result = evaluate("hybrid", eval_id, local_candidate)
        evaluations.append(local_result)
        archive = sorted(archive + [local_result], key=lambda item: item.score, reverse=True)[: max(2, population_size)]

        if current_result is None:
            current_result = local_result
        else:
            delta = local_result.score - current_result.score
            if delta >= 0.0 or rng.random() < math.exp(delta / max(temperature * 20.0, 1e-9)):
                current_result = local_result
        if current_result.score > global_score:
            global_score = current_result.score
            global_best = list(current_result.weights)

        elite_count = min(max(1, population_size // 3), len(archive))
        elites = [item.weights for item in archive[:elite_count]]
        next_particles = [
            Particle(
                position=list(item.weights),
                velocity=[0.0, 0.0, 0.0],
                personal_best=list(item.weights),
                personal_score=item.score,
            )
            for item in archive[:elite_count]
        ]

        inertia = 0.65 - 0.25 * (iteration / max(iterations, 1))
        pso_quota = max(1, (population_size - elite_count) // 2)
        ga_quota = max(0, population_size - elite_count - pso_quota)

        pso_sources = sorted(particles, key=lambda item: item.personal_score, reverse=True)
        for particle in pso_sources:
            if len(next_particles) >= elite_count + pso_quota:
                break
            updated_velocity = []
            for d in range(3):
                r1 = rng.random()
                r2 = rng.random()
                updated_velocity.append(
                    inertia * particle.velocity[d]
                    + 1.35 * r1 * (particle.personal_best[d] - particle.position[d])
                    + 1.35 * r2 * (global_best[d] - particle.position[d])
                )
            pso_position = normalize_weights([particle.position[d] + updated_velocity[d] for d in range(3)])
            next_particles.append(
                Particle(
                    position=pso_position,
                    velocity=updated_velocity,
                    personal_best=list(particle.personal_best),
                    personal_score=particle.personal_score,
                )
            )

        for _ in range(ga_quota):
            if len(elites) >= 2:
                parent_a, parent_b = rng.sample(elites, 2)
                child = crossover_weights(parent_a, parent_b, rng)
            else:
                child = list(global_best)
            child = mutate_weights(child, rng, adaptive_mutation)
            next_particles.append(Particle(position=child, velocity=[0.0, 0.0, 0.0], personal_best=child))

        while len(next_particles) < population_size:
            candidate = mutate_weights(global_best, rng, adaptive_mutation)
            next_particles.append(
                Particle(position=candidate, velocity=[0.0, 0.0, 0.0], personal_best=candidate)
            )

        particles = next_particles[:population_size]

    return evaluations


def write_results(path: Path, evaluations: Sequence[Evaluation]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "method",
                "evaluation_id",
                "scenario",
                "seed",
                "run",
                "score",
                "weight_embb",
                "weight_urllc",
                "weight_mtc",
                "result_dir",
                "log_file",
            ],
        )
        writer.writeheader()
        for item in evaluations:
            writer.writerow(
                {
                    "method": item.method,
                    "evaluation_id": item.evaluation_id,
                    "scenario": item.scenario,
                    "seed": item.seed,
                    "run": item.run,
                    "score": f"{item.score:.6f}",
                    "weight_embb": f"{item.weights[0]:.6f}",
                    "weight_urllc": f"{item.weights[1]:.6f}",
                    "weight_mtc": f"{item.weights[2]:.6f}",
                    "result_dir": str(item.result_dir),
                    "log_file": str(item.log_file),
                }
            )


def write_best(path: Path, evaluations: Sequence[Evaluation]) -> None:
    if not evaluations:
        return
    best = max(evaluations, key=lambda item: item.score)
    payload = {
        "method": best.method,
        "evaluation_id": best.evaluation_id,
        "scenario": best.scenario,
        "seed": best.seed,
        "run": best.run,
        "score": best.score,
        "weights": {
            "eMBB": best.weights[0],
            "URLLC": best.weights[1],
            "MTC": best.weights[2],
        },
        "ns3_args": {
            "baselineMode": "slice_custom",
            "weights": format_weights(best.weights),
        },
        "result_dir": str(best.result_dir),
        "log_file": str(best.log_file),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run metaheuristic optimization over RSLAQ slice_custom weights")
    parser.add_argument("--method", choices=["ga", "pso", "sa", "hybrid", "all"], default="ga")
    parser.add_argument("--scenario", default="normal")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--random_seed", type=int, default=2026)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--population", type=int, default=6)
    parser.add_argument("--mutation_strength", type=float, default=0.12)
    parser.add_argument("--intra_algo", choices=["RR", "PF", "BCQI"], default="PF")
    parser.add_argument("--sim_time", type=float, default=5.0)
    parser.add_argument("--app_start", type=float, default=0.4)
    parser.add_argument("--drain_time", type=float, default=0.2)
    parser.add_argument("--period_ms", type=int, default=10)
    parser.add_argument("--tx_power", type=float, default=43.0)
    parser.add_argument("--tdd_pattern", default="D|D|8D|4GB|4U|U|U")
    parser.add_argument("--rlc_mode", choices=["um", "am"], default="um")
    parser.add_argument("--ns3_dir", type=Path, default=repo_root / "ns-3-dev")
    parser.add_argument("--output_root", type=Path, default=repo_root / "ns-3-dev" / "results_rslaq_metaheuristics")
    parser.add_argument("--build_ns3", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.random_seed)
    search_root = args.output_root / "metaheuristic_search"
    eval_root = search_root / "evals"
    eval_root.mkdir(parents=True, exist_ok=True)

    if args.build_ns3:
        subprocess.run(["./ns3", "build", "rslaq-sim"], cwd=args.ns3_dir, check=True)

    def evaluate(method: str, evaluation_id: int, weights: Sequence[float]) -> Evaluation:
        return run_candidate(
            ns3_dir=args.ns3_dir,
            eval_root=eval_root,
            method=method,
            evaluation_id=evaluation_id,
            scenario=args.scenario,
            weights=weights,
            intra_algo=args.intra_algo,
            sim_time=args.sim_time,
            app_start=args.app_start,
            drain_time=args.drain_time,
            period_ms=args.period_ms,
            seed=args.seed,
            run=args.run,
            tx_power=args.tx_power,
            tdd_pattern=args.tdd_pattern,
            rlc_mode=args.rlc_mode,
        )

    methods = ["ga", "pso", "sa", "hybrid"] if args.method == "all" else [args.method]
    all_evaluations: list[Evaluation] = []
    for method in methods:
        if method == "ga":
            all_evaluations.extend(
                optimize_ga(rng, evaluate, args.iterations, args.population, args.mutation_strength)
            )
        elif method == "pso":
            all_evaluations.extend(optimize_pso(rng, evaluate, args.iterations, args.population))
        elif method == "sa":
            all_evaluations.extend(optimize_sa(rng, evaluate, args.iterations, args.mutation_strength))
        elif method == "hybrid":
            all_evaluations.extend(
                optimize_hybrid(rng, evaluate, args.iterations, args.population, args.mutation_strength)
            )

    write_results(search_root / "metaheuristic_results.csv", all_evaluations)
    write_best(search_root / "best_candidate.json", all_evaluations)
    if all_evaluations:
        best = max(all_evaluations, key=lambda item: item.score)
        print(f"Best {best.method} score={best.score:.4f} weights={format_weights(best.weights)}")
        print(f"Results: {search_root}")


if __name__ == "__main__":
    main()
