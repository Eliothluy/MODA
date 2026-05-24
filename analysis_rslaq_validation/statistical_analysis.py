#!/usr/bin/env python3
"""
Detailed Statistical Analysis of Slice Efficiency
"""

import pandas as pd
import numpy as np
from scipy import stats

# Load the data
df = pd.read_csv("/home/elioth/Documentos/artigo_jussi/analysis_rslaq_validation/slice_efficiency_data.csv")

print("=" * 80)
print("ANÁLISE ESTATÍSTICA DETALHADA DE EFICIÊNCIA DE SLICE")
print("=" * 80)

# Overall statistics
print("\n1. ESTATÍSTICAS GERAIS POR ALGORITMO")
print("-" * 80)

algorithms = df["algorithm"].unique()
for algo in sorted(algorithms):
    algo_data = df[df["algorithm"] == algo]
    print(f"\n{algo}:")
    print(f"  Número de amostras: {len(algo_data)}")

    metrics = {
        "Throughput (Mbps)": "throughput_mean",
        "PDR (%)": "pdr_mean",
        "PLR (%)": "plr_mean",
        "Resource Share (%)": "resource_share_mean",
        "Outage Rate (%)": "outage_rate"
    }

    for name, col in metrics.items():
        if col in algo_data.columns:
            mean = algo_data[col].mean()
            std = algo_data[col].std()
            median = algo_data[col].median()
            min_val = algo_data[col].min()
            max_val = algo_data[col].max()

            if col == "outage_rate":
                mean *= 100
                std *= 100
                median *= 100
                min_val *= 100
                max_val *= 100

            print(f"  {name:25} Média: {mean:6.2f} ± {std:6.2f} | Mediana: {median:6.2f} | Min: {min_val:6.2f} | Max: {max_val:6.2f}")

# Analysis by scenario
print("\n\n2. ESTATÍSTICAS POR CENÁRIO")
print("-" * 80)

scenarios = sorted(df["scenario"].unique())
for scenario in scenarios:
    scenario_data = df[df["scenario"] == scenario]
    print(f"\nCenário: {scenario.upper()}")
    print("-" * 40)

    for algo in sorted(algorithms):
        algo_scenario = scenario_data[scenario_data["algorithm"] == algo]
        if not algo_scenario.empty:
            avg_throughput = algo_scenario["throughput_mean"].mean()
            avg_pdr = algo_scenario["pdr_mean"].mean()
            avg_outage = algo_scenario["outage_rate"].mean() * 100

            print(f"  {algo:30} Thr: {avg_throughput:6.2f} | PDR: {avg_pdr:6.2f}% | Outage: {avg_outage:6.2f}%")

# Analysis by slice
print("\n\n3. ESTATÍSTICAS POR SLICE")
print("-" * 80)

slices = sorted(df["slice"].unique())
for slice_name in slices:
    slice_data = df[df["slice"] == slice_name]
    print(f"\nSlice: {slice_name}")
    print("-" * 40)

    for algo in sorted(algorithms):
        algo_slice = slice_data[slice_data["algorithm"] == algo]
        if not algo_slice.empty:
            avg_throughput = algo_slice["throughput_mean"].mean()
            avg_pdr = algo_slice["pdr_mean"].mean()
            avg_outage = algo_slice["outage_rate"].mean() * 100

            print(f"  {algo:30} Thr: {avg_throughput:6.2f} | PDR: {avg_pdr:6.2f}% | Outage: {avg_outage:6.2f}%")

# Statistical tests
print("\n\n4. TESTES ESTATÍSTICOS (ANOVA)")
print("-" * 80)

for slice_name in slices:
    slice_data = df[df["slice"] == slice_name]
    print(f"\nSlice: {slice_name}")

    # Throughput ANOVA
    groups = [slice_data[slice_data["algorithm"] == algo]["throughput_mean"].values
              for algo in sorted(algorithms)]
    groups = [g for g in groups if len(g) > 0]

    if len(groups) == 3:
        f_stat, p_value = stats.f_oneway(*groups)
        print(f"  Throughput ANOVA - F={f_stat:.2f}, p={p_value:.4f} {'*' if p_value < 0.05 else ''}")

    # PDR ANOVA
    groups = [slice_data[slice_data["algorithm"] == algo]["pdr_mean"].values
              for algo in sorted(algorithms)]
    groups = [g for g in groups if len(g) > 0]

    if len(groups) == 3:
        f_stat, p_value = stats.f_oneway(*groups)
        print(f"  PDR ANOVA - F={f_stat:.2f}, p={p_value:.4f} {'*' if p_value < 0.05 else ''}")

# Best algorithm per metric
print("\n\n5. MELHOR ALGORITMO POR MÉTRICA")
print("-" * 80)

best_throughput = {algo: df[df["algorithm"] == algo]["throughput_mean"].mean() for algo in algorithms}
best_pdr = {algo: df[df["algorithm"] == algo]["pdr_mean"].mean() for algo in algorithms}
lowest_outage = {algo: df[df["algorithm"] == algo]["outage_rate"].mean() for algo in algorithms}

best_algo_thr = max(best_throughput, key=best_throughput.get)
best_algo_pdr = max(best_pdr, key=best_pdr.get)
best_algo_outage = min(lowest_outage, key=lowest_outage.get)

print(f"\n  Melhor Throughput:    {best_algo_thr:30} ({best_throughput[best_algo_thr]:.2f} Mbps)")
print(f"  Melhor PDR:           {best_algo_pdr:30} ({best_pdr[best_algo_pdr]:.2f}%)")
print(f"  Menor Outage Rate:    {best_algo_outage:30} ({lowest_outage[best_algo_outage]*100:.2f}%)")

# Resource efficiency analysis (if available)
print("\n\n6. ANÁLISE DE EFICIÊNCIA DE RECURSOS")
print("-" * 80)

eff_data = df.dropna(subset=["resource_efficiency"])
if not eff_data.empty:
    for algo in sorted(eff_data["algorithm"].unique()):
        algo_eff = eff_data[eff_data["algorithm"] == algo]
        avg_eff = algo_eff["resource_efficiency"].mean()
        avg_need_match = algo_eff["need_allocation_match"].mean()
        print(f"\n  {algo}:")
        print(f"    Eficiência de Recursos: {avg_eff:.4f}")
        print(f"    Match Necessidade-Alocação: {avg_need_match:.4f}")
else:
    print("\n  Dados de eficiência de recursos não disponíveis para alguns algoritmos")

# Performance summary table
print("\n\n7. TABELA RESUMO POR CENÁRIO E SLICE")
print("-" * 80)

print(f"{'Cenário':<20} {'Algoritmo':<30} {'Slice':<8} {'Thr':<10} {'PDR':<8} {'Outage':<10}")
print("-" * 90)

for scenario in scenarios:
    for algo in sorted(algorithms):
        for slice_name in slices:
            row = df[(df["scenario"] == scenario) & (df["algorithm"] == algo) & (df["slice"] == slice_name)]
            if not row.empty:
                thr = row["throughput_mean"].mean()
                pdr = row["pdr_mean"].mean()
                outage = row["outage_rate"].mean() * 100
                print(f"{scenario:<20} {algo:<30} {slice_name:<8} {thr:<10.2f} {pdr:<8.2f} {outage:<10.2f}%")

print("\n" + "=" * 80)
print("FIM DA ANÁLISE")
print("=" * 80)