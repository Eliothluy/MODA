#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("/home/elioth/Documentos/artigo_jussi")
CAMPAIGN = ROOT / "ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency/20260603_125013"
OUT = ROOT / "analysis_rslaq_validation/rslaq_20260603_125013"
TAB = OUT / "tables"
REPORT = OUT / "ROOT_CAUSE_DIAGNOSTIC_RSLAQ_20260603_125013.md"

SLICE_WEIGHTS = {"eMBB": 0.3333, "URLLC": 0.4, "MTC": 0.2667}
DRL_PATTERNS = [
    (re.compile(r"^ddqn_paper_(.+)_seed(\d+)$"), "DDQN-Paper"),
    (re.compile(r"^ddqn_resource_efficient_(.+)_seed(\d+)$"), "DDQN-ResourceEff"),
    (re.compile(r"^sac_paper_(.+)_seed(\d+)$"), "SAC-Paper"),
    (re.compile(r"^sac_resource_efficient_(.+)_seed(\d+)$"), "SAC-ResourceEff"),
    (re.compile(r"^predictive_sac_(.+)_seed(\d+)$"), "Predictive-SAC"),
]


def parse_drl_dir(name: str) -> tuple[str, str, int] | None:
    for pattern, method in DRL_PATTERNS:
        match = pattern.match(name)
        if match:
            return method, match.group(1), int(match.group(2))
    return None


def read_json(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def collect_drl_coverage() -> pd.DataFrame:
    rows = []
    for run_dir in sorted(CAMPAIGN.iterdir()):
        if not run_dir.is_dir():
            continue
        parsed = parse_drl_dir(run_dir.name)
        if parsed is None:
            continue
        method, scenario, label_seed = parsed
        summary_files = list(run_dir.glob("*_summary.json"))
        summary = read_json(summary_files[0]) if summary_files else {}
        step_files = sorted(run_dir.rglob("step_metrics.csv"))
        if not step_files:
            rows.append(
                {
                    "method": method,
                    "scenario": scenario,
                    "label_seed": label_seed,
                    "run_dir": str(run_dir),
                    "step_metrics_path": "",
                    "summary_episodes": summary.get("episodes"),
                    "summary_interaction_budget": summary.get("interaction_budget"),
                    "rows": 0,
                    "episodes_logged": 0,
                    "steps_logged_dedup": 0,
                    "ns3_seed_count": 0,
                    "ns3_seeds": "",
                    "sim_id_count": 0,
                    "terminated_steps": 0,
                    "truncated_steps": 0,
                }
            )
            continue
        for step_file in step_files:
            df = pd.read_csv(
                step_file,
                usecols=lambda c: c in {"seed", "episode", "step", "sim_id", "reward", "terminated", "truncated"},
            )
            dedup = df.drop_duplicates(["episode", "step"]) if {"episode", "step"}.issubset(df.columns) else df
            seeds = ""
            if "seed" in df:
                seed_values = pd.to_numeric(df["seed"], errors="coerce").dropna().astype(int).unique()
                seeds = " ".join(str(v) for v in sorted(seed_values))
            rows.append(
                {
                    "method": method,
                    "scenario": scenario,
                    "label_seed": label_seed,
                    "run_dir": str(run_dir),
                    "step_metrics_path": str(step_file),
                    "summary_episodes": summary.get("episodes"),
                    "summary_interaction_budget": summary.get("interaction_budget"),
                    "final_avg_100": summary.get("final_avg_100"),
                    "best_avg": summary.get("best_avg"),
                    "rows": len(df),
                    "episodes_logged": int(df["episode"].nunique()) if "episode" in df and not df.empty else 0,
                    "episode_min": int(df["episode"].min()) if "episode" in df and not df.empty else np.nan,
                    "episode_max": int(df["episode"].max()) if "episode" in df and not df.empty else np.nan,
                    "steps_logged_dedup": len(dedup),
                    "ns3_seed_count": int(df["seed"].nunique()) if "seed" in df and not df.empty else 0,
                    "ns3_seeds": seeds,
                    "sim_id_count": int(df["sim_id"].nunique()) if "sim_id" in df and not df.empty else 0,
                    "terminated_steps": int(dedup["terminated"].sum()) if "terminated" in dedup else 0,
                    "truncated_steps": int(dedup["truncated"].sum()) if "truncated" in dedup else 0,
                    "mean_reward_logged": float(dedup["reward"].mean()) if "reward" in dedup and not dedup.empty else np.nan,
                }
            )
    return pd.DataFrame(rows)


def summarize_coverage(coverage: pd.DataFrame) -> pd.DataFrame:
    if coverage.empty:
        return coverage
    return coverage.groupby(["method", "scenario"], as_index=False).agg(
        labelled_seeds=("label_seed", "nunique"),
        run_dirs=("run_dir", "nunique"),
        step_files=("step_metrics_path", lambda s: int((s != "").sum())),
        episodes_or_sims=("step_metrics_path", lambda s: int((s != "").sum())),
        steps_logged_mean=("steps_logged_dedup", "mean"),
        steps_logged_min=("steps_logged_dedup", "min"),
        steps_logged_max=("steps_logged_dedup", "max"),
        ns3_seed_count_mean=("ns3_seed_count", "mean"),
        sim_id_count_mean=("sim_id_count", "mean"),
        terminated_steps_sum=("terminated_steps", "sum"),
        truncated_steps_sum=("truncated_steps", "sum"),
    )


def compute_score_variants() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    common = pd.read_csv(TAB / "common_network_by_run_slice_scored.csv")
    common["slice_weight"] = common["slice"].map(SLICE_WEIGHTS).fillna(1 / 3)
    common["score_original_slice"] = common["qos_score_slice"]

    common["score_no_plr_slice"] = common[["throughput_satisfaction", "pdr_score"]].mean(axis=1, skipna=True)
    urllc = common["slice"].eq("URLLC")
    common.loc[urllc, "score_no_plr_slice"] = common.loc[urllc, ["pdr_score", "buffer_score"]].mean(
        axis=1, skipna=True
    )

    common["score_pdr_only_slice"] = common["pdr_score"]
    common["score_thr_pdr_all_slices"] = common[["throughput_satisfaction", "pdr_score"]].mean(axis=1, skipna=True)

    def weighted_scores(group: pd.DataFrame) -> pd.Series:
        weights = group["slice_weight"]
        return pd.Series(
            {
                "score_original": np.average(group["score_original_slice"], weights=weights),
                "score_no_plr": np.average(group["score_no_plr_slice"], weights=weights),
                "score_pdr_only": np.average(group["score_pdr_only_slice"], weights=weights),
                "score_thr_pdr_all_slices": np.average(group["score_thr_pdr_all_slices"], weights=weights),
            }
        )

    by_run = common.groupby(["method", "scenario", "seed", "source"], as_index=False).apply(weighted_scores)
    if isinstance(by_run.index, pd.MultiIndex):
        by_run = by_run.reset_index(drop=True)
    ranking = by_run.groupby(["method", "source"], as_index=False).agg(
        runs=("score_original", "count"),
        score_original=("score_original", "mean"),
        score_no_plr=("score_no_plr", "mean"),
        score_pdr_only=("score_pdr_only", "mean"),
        score_thr_pdr_all_slices=("score_thr_pdr_all_slices", "mean"),
    )
    ranking = ranking.sort_values("score_no_plr", ascending=False)

    comparisons = []
    for scenario, scenario_df in by_run.groupby("scenario"):
        drl = scenario_df[scenario_df["source"].eq("DRL-late-training")]
        baseline = scenario_df[scenario_df["source"].eq("baseline")]
        if drl.empty or baseline.empty:
            continue
        for score_col in ["score_original", "score_no_plr", "score_pdr_only", "score_thr_pdr_all_slices"]:
            drl_mean = drl.groupby("method", as_index=False)[score_col].mean().sort_values(score_col, ascending=False)
            baseline_mean = baseline.groupby("method", as_index=False)[score_col].mean().sort_values(score_col, ascending=False)
            best_drl = drl_mean.iloc[0]
            best_base = baseline_mean.iloc[0]
            comparisons.append(
                {
                    "scenario": scenario,
                    "score_variant": score_col,
                    "best_drl_method": best_drl["method"],
                    "best_drl_score": best_drl[score_col],
                    "best_baseline_method": best_base["method"],
                    "best_baseline_score": best_base[score_col],
                    "gap_pct": 100.0 * (best_drl[score_col] - best_base[score_col]) / abs(best_base[score_col]),
                }
            )
    return common, by_run, pd.DataFrame(comparisons), ranking


def detect_incomplete_runs(coverage_summary: pd.DataFrame) -> pd.DataFrame:
    if coverage_summary.empty:
        return coverage_summary
    df = coverage_summary.copy()
    df["expected_labelled_seeds"] = 5
    df["missing_labelled_seeds"] = df["expected_labelled_seeds"] - df["labelled_seeds"]
    df["has_incomplete_seed_coverage"] = df["missing_labelled_seeds"] > 0
    df["has_short_episodes"] = df["steps_logged_mean"] < 90
    df["has_many_terminations"] = df["terminated_steps_sum"] > 0
    return df[
        df[["has_incomplete_seed_coverage", "has_short_episodes", "has_many_terminations"]].any(axis=1)
    ].copy()


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    if df.empty:
        return "_Sem dados._"
    display = df[columns].head(max_rows).copy()
    for col in display.select_dtypes(include=["float"]).columns:
        display[col] = display[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    display = display.fillna("").astype(str)
    header = "| " + " | ".join(display.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(display.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in display.to_numpy()]
    return "\n".join([header, separator, *rows])


def write_report(
    coverage_summary: pd.DataFrame,
    incomplete: pd.DataFrame,
    comparisons: pd.DataFrame,
    ranking: pd.DataFrame,
) -> None:
    lines = [
        "# Diagnostico de causa-raiz do protocolo RSLAQ",
        "",
        "## Conclusao curta",
        "",
        "A campanha atual nao prova que as DRLs sao intrinsecamente piores que RR/PF/BCQI. Ela prova que, com o protocolo atual, os KPIs logados durante treino/exploracao ficam abaixo dos baselines. A causa mais provavel e experimental: avaliacao misturada com treino, acoes exploratorias/estocasticas, cobertura incompleta em alguns casos, terminacoes precoces no Predictive-SAC e score original com dupla contagem efetiva de perda via PDR e PLR.",
        "",
        "## Evidencias principais",
        "",
        "- O runner usa `SEED_CYCLE=999999`; assim, a seed do ns-3 fica fixa dentro de uma execucao longa, salvo campanhas muito maiores que esse ciclo.",
        "- DDQN registra KPIs enquanto ainda usa epsilon-greedy; o padrao tem `epsilon_min=0.05`, portanto a avaliacao tardia ainda inclui exploracao.",
        "- SAC e Predictive-SAC registram KPIs usando `actor.sample`, portanto as acoes logadas sao amostras estocasticas, nao a media deterministica da politica.",
        "- A comparacao atual usa o trecho final do treinamento como proxy de avaliacao; isso nao substitui avaliacao pos-treino com politica congelada.",
        "- `Predictive-SAC` apresenta muitos episodios curtos/terminados; nesses casos a comparacao mede falhas de horizonte curto, nao desempenho estacionario.",
        "- O score original inclui `pdr_score` e `plr_score`. Para DRL, `pdr_pct = 100 - plr_pct`; para baseline, `plr_pct` aparece 0 mesmo quando `pdr_pct < 100`. Isso favorece baseline por construcao e duplica a penalizacao de perda na DRL.",
        "",
        "## Cobertura e runs suspeitos",
        "",
        markdown_table(
            incomplete,
            [
                "method",
                "scenario",
                "labelled_seeds",
                "step_files",
                "steps_logged_mean",
                "terminated_steps_sum",
                "missing_labelled_seeds",
                "has_short_episodes",
            ],
            30,
        ),
        "",
        "## Sensibilidade do score",
        "",
        "`score_original` reproduz o score do relatorio anterior. `score_no_plr` remove a dupla contagem direta de `PLR`, mantendo throughput/PDR para eMBB/MTC e PDR/buffer para URLLC.",
        "",
        markdown_table(
            comparisons.sort_values(["scenario", "score_variant"]),
            [
                "scenario",
                "score_variant",
                "best_drl_method",
                "best_drl_score",
                "best_baseline_method",
                "best_baseline_score",
                "gap_pct",
            ],
            40,
        ),
        "",
        "## Ranking medio por variante",
        "",
        markdown_table(
            ranking,
            ["method", "source", "runs", "score_original", "score_no_plr", "score_pdr_only", "score_thr_pdr_all_slices"],
            20,
        ),
        "",
        "## Protocolo recomendado antes de concluir cientificamente",
        "",
        "1. Treinar a politica com uma seed de treino registrada, mas avaliar em uma fase separada com politica congelada.",
        "2. DDQN: avaliacao com `epsilon=0` e sem replay/update durante os episodios de avaliacao.",
        "3. SAC/Predictive-SAC: avaliacao com acao deterministica baseada em `tanh(mean)`, nao `actor.sample`.",
        "4. Separar `training_seed`, `ns3_seed` e `replicate_id`; repetir `seed=1` tres vezes sem mudar RNG nao e uma replica independente.",
        "5. Executar pelo menos `5 ns3_seeds x 3 training_replicates` por metodo/cenario, ou `15` seeds independentes por metodo/cenario, com todos os metodos no mesmo conjunto de cargas.",
        "6. Comparar primeiro por metricas fisicas comuns: throughput por slice, PDR, buffer URLLC, delay/jitter quando disponivel, SLA/outage rate e eficiencia de recurso. Reward deve ficar separado por modo (`paper` vs `resource_efficient`).",
        "7. Corrigir o score composto: usar PDR ou PLR, nao ambos, salvo se os logs de baseline e DRL tiverem semantica identica para perda.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    coverage = collect_drl_coverage()
    coverage_summary = summarize_coverage(coverage)
    incomplete = detect_incomplete_runs(coverage_summary)
    common_variants, score_variants, comparisons, ranking = compute_score_variants()

    coverage.to_csv(TAB / "drl_run_coverage_diagnostics.csv", index=False)
    coverage_summary.to_csv(TAB / "drl_coverage_summary_by_method_scenario.csv", index=False)
    incomplete.to_csv(TAB / "drl_incomplete_or_early_terminated_runs.csv", index=False)
    common_variants.to_csv(TAB / "common_network_score_variants_by_slice.csv", index=False)
    score_variants.to_csv(TAB / "network_score_variants_by_run.csv", index=False)
    comparisons.to_csv(TAB / "drl_vs_baseline_score_variant_sensitivity.csv", index=False)
    ranking.to_csv(TAB / "method_ranking_score_variants.csv", index=False)
    write_report(coverage_summary, incomplete, comparisons, ranking)
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
