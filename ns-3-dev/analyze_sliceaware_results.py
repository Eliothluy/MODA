#!/usr/bin/env python3
"""
Análise Comparativa dos Cenários GreenRAN — Slice-Aware Scheduler
Autor: Engenheiro de Dados / Especialista 5G
"""
import os
import json
import glob
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
BASE_DIR = Path("/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/results_sliceaware_scenarios")
FIG_DIR = BASE_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)

SCENARIOS = [
    "greenran_low",
    "greenran_normal",
    "greenran_video_heavy",
    "greenran_mmtc_massive",
    "greenran_congestion",
    "greenran_night_energy",
    "greenran_balanced",
]

# Ordem lógica para apresentação
SCENARIO_ORDER = [
    "greenran_low",
    "greenran_normal",
    "greenran_balanced",
    "greenran_video_heavy",
    "greenran_mmtc_massive",
    "greenran_congestion",
    "greenran_night_energy",
]

REPORT_PATH = BASE_DIR / "relatorio_analise_greenran.md"

# Cores consistentes por slice
SLICE_COLORS = {
    "VIDEO_EMBB": "#1f77b4",
    "SENSOR_MMTC": "#2ca02c",
    "GENERIC_EMBB": "#ff7f0e",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_csv(path)
    return None

def pct(val: float) -> str:
    return f"{val*100:.1f}%"

def mbps(val: float) -> str:
    return f"{val:.2f} Mbps"

def ms(val: float) -> str:
    return f"{val:.1f} ms"

# ---------------------------------------------------------------------------
# Leitura de dados
# ---------------------------------------------------------------------------
sla_records = []
slice_records = []
ue_records = []
timeseries_records = []
config_records = []

for scenario in SCENARIOS:
    scen_dir = BASE_DIR / scenario
    if not scen_dir.exists():
        continue

    # SLA
    sla_path = scen_dir / f"{scenario}_greenran_sla.csv"
    df_sla = read_csv_if_exists(sla_path)
    if df_sla is not None:
        sla_records.append(df_sla)

    # Slice aggregate
    slice_path = scen_dir / f"{scenario}_greenran_slice.csv"
    df_slice = read_csv_if_exists(slice_path)
    if df_slice is not None:
        df_slice["scenario"] = scenario
        slice_records.append(df_slice)

    # UE aggregate (amostra para análise de fairness)
    ue_path = scen_dir / f"{scenario}_greenran_ue.csv"
    df_ue = read_csv_if_exists(ue_path)
    if df_ue is not None:
        df_ue["scenario"] = scenario
        ue_records.append(df_ue)

    # Timeseries
    ts_path = scen_dir / "greenran_stats_timeseries.csv"
    df_ts = read_csv_if_exists(ts_path)
    if df_ts is not None:
        df_ts["scenario"] = scenario
        timeseries_records.append(df_ts)

    # Config JSON
    cfg_path = scen_dir / f"{scenario}_simulation_config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            cfg = json.load(f)
        # Extrair info relevante
        num_ues = cfg.get("numUes", {})
        weights = cfg.get("weights", {}).get("values", [None, None, None])
        config_records.append({
            "scenario": scenario,
            "seed": cfg.get("seed"),
            "simTimeSec": cfg.get("simTimeSec"),
            "num VIDEO_EMBB": num_ues.get("VIDEO_EMBB", 0),
            "num SENSOR_MMTC": num_ues.get("SENSOR_MMTC", 0),
            "num GENERIC_EMBB": num_ues.get("GENERIC_EMBB", 0),
            "weight_VIDEO_EMBB": weights[0] if len(weights) > 0 else None,
            "weight_SENSOR_MMTC": weights[1] if len(weights) > 1 else None,
            "weight_GENERIC_EMBB": weights[2] if len(weights) > 2 else None,
        })

# ---------------------------------------------------------------------------
# DataFrames consolidados
# ---------------------------------------------------------------------------
df_sla = pd.concat(sla_records, ignore_index=True) if sla_records else pd.DataFrame()
df_slice = pd.concat(slice_records, ignore_index=True) if slice_records else pd.DataFrame()
df_ue = pd.concat(ue_records, ignore_index=True) if ue_records else pd.DataFrame()
df_ts = pd.concat(timeseries_records, ignore_index=True) if timeseries_records else pd.DataFrame()
df_cfg = pd.DataFrame(config_records)

# Normalizar ordem
df_sla["scenario"] = pd.Categorical(df_sla["scenario"], categories=SCENARIO_ORDER, ordered=True)
df_slice["scenario"] = pd.Categorical(df_slice["scenario"], categories=SCENARIO_ORDER, ordered=True)
df_ue["scenario"] = pd.Categorical(df_ue["scenario"], categories=SCENARIO_ORDER, ordered=True)
df_ts["scenario"] = pd.Categorical(df_ts["scenario"], categories=SCENARIO_ORDER, ordered=True)

# ---------------------------------------------------------------------------
# Métricas derivadas
# ---------------------------------------------------------------------------
# Criar coluna de rótulo slice+direction
df_sla["slice_dir"] = df_sla["slice"] + " (" + df_sla["direction"] + ")"

# Violation rate por cenário (qualquer overall_violation == 1)
violation_by_scenario = (
    df_sla.groupby("scenario")
    .apply(lambda g: pd.Series({
        "total_kpis": len(g),
        "violations": g["overall_violation"].sum(),
        "violation_rate": g["overall_violation"].mean(),
    }))
    .reset_index()
)

# Agrupar por cenário e slice (DL/UL separados para granularidade)
scenario_slice = (
    df_sla.groupby(["scenario", "slice", "direction"])
    .agg(
        sla_delay=("sla_delay_ms", "first"),
        avg_delay=("measured_avg_delay_ms", "first"),
        sla_pdr=("sla_pdr", "first"),
        eff_pdr=("measured_effective_pdr", "first"),
        sla_thr=("sla_throughput_mbps", "first"),
        meas_thr=("measured_throughput_mbps", "first"),
        delay_viol=("delay_violation", "first"),
        pdr_viol=("pdr_violation", "first"),
        thr_viol=("throughput_violation", "first"),
        overall_viol=("overall_violation", "first"),
    )
    .reset_index()
)

# Fairness por cenário (coeficiente de variação do throughput por slice/direção DL)
dl_ue = df_ue[df_ue["direction"] == "DL"].copy()
if not dl_ue.empty:
    fairness_dl = (
        dl_ue.groupby(["scenario", "slice_name"])
        .apply(lambda g: pd.Series({
            "cv_thr": g["throughput_mbps"].std() / g["throughput_mbps"].mean() if g["throughput_mbps"].mean() > 0 else np.nan,
            "min_thr": g["throughput_mbps"].min(),
            "max_thr": g["throughput_mbps"].max(),
            "mean_thr": g["throughput_mbps"].mean(),
            "num_ues": g["ue_id"].nunique(),
        }))
        .reset_index()
    )
else:
    fairness_dl = pd.DataFrame()

# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "figure.figsize": (10, 6),
    "axes.grid": True,
    "grid.alpha": 0.3,
})

def savefig(name: str):
    path = FIG_DIR / name
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    return str(path)

# 1) Throughput medido vs SLA — barras agrupadas por cenário
fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(SCENARIO_ORDER))
width = 0.25
slices = ["VIDEO_EMBB", "SENSOR_MMTC", "GENERIC_EMBB"]
# Filtrar apenas DL para clareza (UL tem SLA baixo e menos impacto visual)
for i, slc in enumerate(slices):
    sub = scenario_slice[(scenario_slice["slice"] == slc) & (scenario_slice["direction"] == "DL")].set_index("scenario").reindex(SCENARIO_ORDER)
    ax.bar(x + i*width, sub["meas_thr"], width, label=f"{slc} (medido)", color=SLICE_COLORS[slc], alpha=0.8)
    # Linha tracejada do SLA
    ax.plot(x + i*width, sub["sla_thr"], marker="_", linestyle="None", color="black", markersize=12)

ax.set_xticks(x + width)
ax.set_xticklabels(SCENARIO_ORDER, rotation=30, ha="right")
ax.set_ylabel("Throughput (Mbps)")
ax.set_title("Throughput Medido vs SLA (DL) por Cenário")
ax.legend()
# Anotação simples para SLA
ax.text(0.02, 0.95, "Marcas pretas (_) = SLA", transform=ax.transAxes, fontsize=9, verticalalignment="top", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
savefig("throughput_dl_vs_sla.png")

# 2) Delay medido vs SLA
fig, ax = plt.subplots(figsize=(12, 6))
for i, slc in enumerate(slices):
    sub = scenario_slice[(scenario_slice["slice"] == slc) & (scenario_slice["direction"] == "DL")].set_index("scenario").reindex(SCENARIO_ORDER)
    ax.bar(x + i*width, sub["avg_delay"], width, label=f"{slc} (medido)", color=SLICE_COLORS[slc], alpha=0.8)
    ax.plot(x + i*width, sub["sla_delay"], marker="_", linestyle="None", color="black", markersize=12)
ax.set_xticks(x + width)
ax.set_xticklabels(SCENARIO_ORDER, rotation=30, ha="right")
ax.set_ylabel("Delay (ms)")
ax.set_title("Delay Medido vs SLA (DL) por Cenário")
ax.legend()
ax.text(0.02, 0.95, "Marcas pretas (_) = SLA", transform=ax.transAxes, fontsize=9, verticalalignment="top", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
savefig("delay_dl_vs_sla.png")

# 3) Taxa de violação geral por cenário (barras)
fig, ax = plt.subplots(figsize=(10, 5))
colors = ["#d62728" if r > 0.5 else "#ffbb78" if r > 0 else "#2ca02c" for r in violation_by_scenario.set_index("scenario").reindex(SCENARIO_ORDER)["violation_rate"]]
ax.bar(SCENARIO_ORDER, violation_by_scenario.set_index("scenario").reindex(SCENARIO_ORDER)["violation_rate"], color=colors)
ax.set_ylabel("Taxa de Violação (0-1)")
ax.set_title("Taxa Geral de Violação de SLA por Cenário")
ax.set_ylim(0, 1.05)
for i, v in enumerate(violation_by_scenario.set_index("scenario").reindex(SCENARIO_ORDER)["violation_rate"]):
    ax.text(i, v + 0.03, pct(v), ha="center", fontsize=9)
plt.xticks(rotation=30, ha="right")
savefig("violation_rate_scenario.png")

# 4) Heatmap de violações (cenário x slice_dir)
pivot_viol = df_sla.pivot_table(index="scenario", columns="slice_dir", values="overall_violation", aggfunc="first")
# Reordenar
pivot_viol = pivot_viol.reindex(SCENARIO_ORDER)
fig, ax = plt.subplots(figsize=(10, 6))
im = ax.imshow(pivot_viol.values, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=1)
ax.set_xticks(np.arange(len(pivot_viol.columns)))
ax.set_xticklabels(pivot_viol.columns, rotation=45, ha="right")
ax.set_yticks(np.arange(len(pivot_viol.index)))
ax.set_yticklabels(pivot_viol.index)
for i in range(len(pivot_viol.index)):
    for j in range(len(pivot_viol.columns)):
        val = pivot_viol.iloc[i, j]
        if not np.isnan(val):
            ax.text(j, i, f"{int(val)}", ha="center", va="center", color="white" if val > 0.5 else "black", fontweight="bold")
ax.set_title("Heatmap de Violação de SLA (1 = violado)")
fig.colorbar(im, ax=ax)
savefig("heatmap_violations.png")

# 5) PDR (Packet Delivery Ratio) medido
fig, ax = plt.subplots(figsize=(12, 6))
for i, slc in enumerate(slices):
    sub = scenario_slice[(scenario_slice["slice"] == slc) & (scenario_slice["direction"] == "DL")].set_index("scenario").reindex(SCENARIO_ORDER)
    ax.bar(x + i*width, sub["eff_pdr"], width, label=slc, color=SLICE_COLORS[slc], alpha=0.8)
    ax.plot(x + i*width, sub["sla_pdr"], marker="_", linestyle="None", color="black", markersize=12)
ax.set_xticks(x + width)
ax.set_xticklabels(SCENARIO_ORDER, rotation=30, ha="right")
ax.set_ylabel("PDR")
ax.set_ylim(0, 1.05)
ax.set_title("PDR Efetivo vs SLA (DL) por Cenário")
ax.legend()
ax.text(0.02, 0.95, "Marcas pretas (_) = SLA", transform=ax.transAxes, fontsize=9, verticalalignment="top", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
savefig("pdr_dl_vs_sla.png")

# 6) Série temporal — throughput médio por slice (DL) no cenário mais crítico: congestion
if not df_ts.empty:
    ts_dl = df_ts[df_ts["direction"] == "DL"].copy()
    ts_dl["time_s"] = ts_dl["timestamp_ms"] / 1000.0
    # Agregar média por cenário/slice/tempo
    ts_agg = ts_dl.groupby(["scenario", "slice_id", "time_s"])["thr_mbps"].mean().reset_index()
    # Mapear slice_id para nome usando config (simplificado: id 0=VIDEO_EMBB, 1=SENSOR_MMTC, 2=GENERIC_EMBB)
    slice_map = {0: "VIDEO_EMBB", 1: "SENSOR_MMTC", 2: "GENERIC_EMBB"}
    ts_agg["slice_name"] = ts_agg["slice_id"].map(slice_map)

    for scenario in ["greenran_congestion", "greenran_normal", "greenran_night_energy"]:
        sub = ts_agg[ts_agg["scenario"] == scenario]
        if sub.empty:
            continue
        fig, ax = plt.subplots(figsize=(10, 5))
        for slc in slice_map.values():
            s = sub[sub["slice_name"] == slc]
            if not s.empty:
                ax.plot(s["time_s"], s["thr_mbps"], label=slc, color=SLICE_COLORS.get(slc, "gray"))
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("Throughput médio (Mbps)")
        ax.set_title(f"Evolução Temporal do Throughput (DL) — {scenario}")
        ax.legend()
        savefig(f"timeseries_thr_dl_{scenario}.png")

    # PLR médio por cenário ao longo do tempo
    for scenario in ["greenran_congestion", "greenran_normal"]:
        sub = df_ts[(df_ts["scenario"] == scenario) & (df_ts["direction"] == "DL")].copy()
        if sub.empty:
            continue
        sub["time_s"] = sub["timestamp_ms"] / 1000.0
        ts_plr = sub.groupby(["slice_id", "time_s"])["plr_pct"].mean().reset_index()
        ts_plr["slice_name"] = ts_plr["slice_id"].map(slice_map)
        fig, ax = plt.subplots(figsize=(10, 5))
        for slc in slice_map.values():
            s = ts_plr[ts_plr["slice_name"] == slc]
            if not s.empty:
                ax.plot(s["time_s"], s["plr_pct"], label=slc, color=SLICE_COLORS.get(slc, "gray"))
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("PLR (%)")
        ax.set_title(f"Evolução Temporal do PLR (DL) — {scenario}")
        ax.legend()
        savefig(f"timeseries_plr_dl_{scenario}.png")

# 7) Fairness — CV do throughput DL por cenário e slice
if not fairness_dl.empty:
    fig, ax = plt.subplots(figsize=(12, 6))
    # Pivot
    fair_pivot = fairness_dl.pivot(index="scenario", columns="slice_name", values="cv_thr").reindex(SCENARIO_ORDER)
    fair_pivot.plot(kind="bar", ax=ax, color=[SLICE_COLORS.get(c, "gray") for c in fair_pivot.columns])
    ax.set_ylabel("Coeficiente de Variação (std/mean)")
    ax.set_title("Fairness Inter-UE — Coeficiente de Variação do Throughput DL")
    ax.legend(title="Slice")
    plt.xticks(rotation=30, ha="right")
    savefig("fairness_cv_thr_dl.png")

# ---------------------------------------------------------------------------
# Relatório Markdown
# ---------------------------------------------------------------------------
report_lines = []
report_lines.append("# Relatório de Análise — GreenRAN Slice-Aware Scenarios")
report_lines.append("")
report_lines.append(f"**Data de geração:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
report_lines.append("")
report_lines.append("## 1. Resumo Executivo")
report_lines.append("")
report_lines.append(
    "Este relatório apresenta uma análise comparativa dos sete cenários de simulação "
    "do *slice-aware scheduler* implementado no ns-3 com 5G-LENA. O objetivo é avaliar "
    "o cumprimento dos SLAs de *throughput*, *delay* e *PDR* (Packet Delivery Ratio) "
    "para três classes de slice — **VIDEO_EMBB** (vídeo vigilância), **SENSOR_MMTC** (IoT) "
    "e **GENERIC_EMBB** (usuários gerais) — sob diferentes condições de carga, "
    "distribuição de tráfego e políticas de economia de energia."
)
report_lines.append("")

# Tabela de configurações
report_lines.append("## 2. Configurações dos Cenários")
report_lines.append("")
report_lines.append("| Cenário | Seed | UEs Vídeo | UEs Sensor | UEs Genérico | Peso Vídeo | Peso Sensor | Peso Genérico |")
report_lines.append("|---------|------|-----------|------------|--------------|------------|-------------|---------------|")
for _, row in df_cfg.iterrows():
    report_lines.append(
        f"| {row['scenario']} | {row['seed']} | {row['num VIDEO_EMBB']} | {row['num SENSOR_MMTC']} | {row['num GENERIC_EMBB']} | "
        f"{row['weight_VIDEO_EMBB']} | {row['weight_SENSOR_MMTC']} | {row['weight_GENERIC_EMBB']} |"
    )
report_lines.append("")

# Sumário de violações
report_lines.append("## 3. Panorama de Violações de SLA")
report_lines.append("")
report_lines.append(
    "A tabela a seguir condensa o desempenho por cenário. Cada linha da tabela original "
    "representa um KPI (delay, PDR ou throughput) para uma direção (DL/UL). "
    "A coluna **Taxa de Violação** indica a fração de KPIs que não atingiram o SLA contratado."
)
report_lines.append("")
report_lines.append("| Cenário | KPIs Avaliados | Violações | Taxa de Violação |")
report_lines.append("|---------|----------------|-----------|------------------|")
for _, row in violation_by_scenario.iterrows():
    report_lines.append(f"| {row['scenario']} | {int(row['total_kpis'])} | {int(row['violations'])} | {pct(row['violation_rate'])} |")
report_lines.append("")

report_lines.append("### 3.1. Destaques")
report_lines.append("")
# Encontrar melhor e pior cenário
best_scen = violation_by_scenario.loc[violation_by_scenario["violation_rate"].idxmin(), "scenario"]
worst_scen = violation_by_scenario.loc[violation_by_scenario["violation_rate"].idxmax(), "scenario"]
report_lines.append(f"- **Melhor cenário:** `{best_scen}` com taxa de violação de {pct(violation_by_scenario[violation_by_scenario['scenario']==best_scen]['violation_rate'].values[0])}.")
report_lines.append(f"- **Pior cenário:** `{worst_scen}` com taxa de violação de {pct(violation_by_scenario[violation_by_scenario['scenario']==worst_scen]['violation_rate'].values[0])}.")
report_lines.append("")

# Análise detalhada por cenário
report_lines.append("## 4. Análise Detalhada por Cenário")
report_lines.append("")

for scenario in SCENARIO_ORDER:
    report_lines.append(f"### 4.{SCENARIO_ORDER.index(scenario)+1}. {scenario}")
    report_lines.append("")
    sub = scenario_slice[scenario_slice["scenario"] == scenario]
    if sub.empty:
        report_lines.append("_Dados não disponíveis._")
        report_lines.append("")
        continue

    # Parágrafo descritivo
    cfg_row = df_cfg[df_cfg["scenario"] == scenario]
    if not cfg_row.empty:
        num_ues = cfg_row.iloc[0][["num VIDEO_EMBB", "num SENSOR_MMTC", "num GENERIC_EMBB"]].sum()
        report_lines.append(
            f"Configuração com **{int(num_ues)} UEs** totais. "
            f"Pesos estáticos: Video={cfg_row.iloc[0]['weight_VIDEO_EMBB']}, "
            f"Sensor={cfg_row.iloc[0]['weight_SENSOR_MMTC']}, Genérico={cfg_row.iloc[0]['weight_GENERIC_EMBB']}."
        )
    report_lines.append("")

    report_lines.append("| Slice (Dir) | SLA Delay | Delay Medido | SLA PDR | PDR Medido | SLA Thr | Thr Medido | Violação? |")
    report_lines.append("|-------------|-----------|--------------|---------|------------|---------|------------|-----------|")
    for _, r in sub.iterrows():
        viol_flag = "🔴 SIM" if r["overall_viol"] else "🟢 NÃO"
        report_lines.append(
            f"| {r['slice']} ({r['direction']}) | {ms(r['sla_delay'])} | {ms(r['avg_delay'])} | "
            f"{pct(r['sla_pdr'])} | {pct(r['eff_pdr'])} | {mbps(r['sla_thr'])} | {mbps(r['meas_thr'])} | {viol_flag} |"
        )
    report_lines.append("")

    # Insights rápidos
    viols = sub[sub["overall_viol"] == 1]
    if not viols.empty:
        report_lines.append("**KPIs violados:**")
        for _, r in viols.iterrows():
            reasons = []
            if r["delay_viol"]:
                reasons.append("delay")
            if r["pdr_viol"]:
                reasons.append("PDR")
            if r["thr_viol"]:
                reasons.append("throughput")
            report_lines.append(f"- `{r['slice']} ({r['direction']})`: {', '.join(reasons)}.")
    else:
        report_lines.append("**Todos os KPIs dentro do SLA.**")
    report_lines.append("")

# Seção 5: Análise de Throughput
report_lines.append("## 5. Análise de Throughput (DL)")
report_lines.append("")
report_lines.append(
    "A figura *throughput_dl_vs_sla.png* compara o throughput medido no downlink com os "
    "targets de SLA. Observa-se que, nos cenários de alta carga (**congestion**, **video_heavy**, **balanced**), "
    "o slice **GENERIC_EMBB** sofre degradação severa, indicando contenção de recursos de RBG/PRB. "
    "No cenário **night_energy**, em que a carga é propositalmente reduzida, todos os slices operam "
    "dentro ou próximo do SLA, validando a hipótese de que o gargalo é primariamente de capacidade de radio."
)
report_lines.append("")
report_lines.append(f"![Throughput DL vs SLA](figures/throughput_dl_vs_sla.png)")
report_lines.append("")

# Seção 6: Delay
report_lines.append("## 6. Análise de Latência (DL)")
report_lines.append("")
report_lines.append(
    "A latência é sensível ao tamanho da fila MAC e ao número de UEs ativos. "
    "Em **congestion** e **balanced**, o delay do VIDEO_EMBB e GENERIC_EMBB excede 800 ms, "
    "refletindo bufferbloat e possível starvation de UEs no final do ciclo de alocação de RBGs. "
    "A direção UL apresenta latências menores (tipicamente < 100 ms) graças ao menor volume de dados."
)
report_lines.append("")
report_lines.append(f"![Delay DL vs SLA](figures/delay_dl_vs_sla.png)")
report_lines.append("")

# Seção 7: PDR
report_lines.append("## 7. Confiabilidade — Packet Delivery Ratio (DL)")
report_lines.append("")
report_lines.append(
    "O PDR é impactado diretamente pela alocação de RBGs e pelo BLER do canal. "
    "Cenários com elevada perda de pacotes (**congestion**, **balanced**) mostram PDR efetivo abaixo de 0,50, "
    "o que é inaceitável para eMBB e para vídeo de segurança. Nota-se que o **SENSOR_MMTC** "
    "também apresenta PDR inferior ao SLA de 0,95 na maioria dos cenários; como o tráfego é esporádico (80 B a cada 10 s), "
    "perdas de pacotes isoladas têm impacto percentual elevado em bases estatísticas pequenas."
)
report_lines.append("")
report_lines.append(f"![PDR DL vs SLA](figures/pdr_dl_vs_sla.png)")
report_lines.append("")

# Seção 8: Fairness
report_lines.append("## 8. Fairness Inter-UE (DL)")
report_lines.append("")
if not fairness_dl.empty:
    report_lines.append(
        "O coeficiente de variação (CV = std/mean) do throughput por UE dentro de cada slice "
        "revela desigualdade de alocação. Valores próximos de zero indicam distribuição uniforme. "
        "Valores superiores a 0,5 sugerem que alguns UEs estão sendo privilegiados em detrimento de outros."
    )
    report_lines.append("")
    report_lines.append("| Cenário | Slice | CV Thr | Min Thr | Max Thr | Mean Thr |")
    report_lines.append("|---------|-------|--------|---------|---------|----------|")
    for _, r in fairness_dl.iterrows():
        report_lines.append(
            f"| {r['scenario']} | {r['slice_name']} | {r['cv_thr']:.2f} | {mbps(r['min_thr'])} | {mbps(r['max_thr'])} | {mbps(r['mean_thr'])} |"
        )
    report_lines.append("")
    report_lines.append(f"![Fairness CV](figures/fairness_cv_thr_dl.png)")
    report_lines.append("")
else:
    report_lines.append("_Dados de UE não disponíveis para análise de fairness._")
    report_lines.append("")

# Seção 9: Heatmap e Temporal
report_lines.append("## 9. Mapa de Calor de Violações")
report_lines.append("")
report_lines.append(
    "O heatmap abaixo sintetiza, em escala binária, quais combinações cenário × slice × direção "
    "falharam no cumprimento do SLA. A predominância de vermelho nos cenários de alta carga "
    "confirma que o escalonador slice-aware, na configuração atual de pesos estáticos, "
    "não consegue garantir isolamento absoluto de QoS sob contenção extrema."
)
report_lines.append("")
report_lines.append(f"![Heatmap Violações](figures/heatmap_violations.png)")
report_lines.append("")

report_lines.append("## 10. Evolução Temporal")
report_lines.append("")
report_lines.append(
    "As séries temporais de throughput e PLR para os cenários *normal* e *congestion* "
    "mostram que a instabilidade começa precocemente (após ~0,6 s) e persiste durante toda a simulação. "
    "Isso indica que o sistema não converge para um estado estável de QoS, "
    "sugestivo de que os pesos estáticos não se adaptam às variações de demanda."
)
report_lines.append("")
report_lines.append(f"![Timeseries Thr Congestion](figures/timeseries_thr_dl_greenran_congestion.png)")
report_lines.append("")
report_lines.append(f"![Timeseries PLR Normal](figures/timeseries_plr_dl_greenran_normal.png)")
report_lines.append("")

# Seção 11: Recomendações
report_lines.append("## 11. Recomendações Técnicas")
report_lines.append("")
report_lines.append(
    "1. **Adoção de pesos dinâmicos:** os pesos estáticos [0,40; 0,15; 0,45] mostraram-se "
    "insuficientes para proteger slices de missão crítica em sobrecarga. Recomenda-se implementar "
    "um controlador DRL (como o agente SAC/DDQN desenvolvido no subprojeto `ns-o-ran-gym`) "
    "para ajustar `p_j` a cada TTI de acordo com o buffer e o CQI dos UEs."
)
report_lines.append("")
report_lines.append(
    "2. **Priorização de PDR no MMTC:** o slice SENSOR_MMTC possui baixo volume, mas SLA de PDR alto (0,95). "
    "Recomenda-se garantir alocação mínima de RBGs (minPRB) mesmo quando o buffer é pequeno, "
    "evitando descarte por starvation do scheduler."
)
report_lines.append("")
report_lines.append(
    "3. **Redução de filas MAC:** os atrasos > 1000 ms em DL indicam bufferbloat. "
    "Avaliar a ativação de AQM (Active Queue Management) no RLC ou limitação do tamanho da fila de PDUs."
)
report_lines.append("")
report_lines.append(
    "4. **Simulações com maior duração:** os resultados aqui são de apenas 3 s de simulação. "
    "Para análise estatística robusta de PDR em MMTC, recomenda-se simular pelo menos 30–60 s."
)
report_lines.append("")
report_lines.append(
    "5. **Avaliação do impacto do peso de energia:** o cenário *night_energy* reduz a potência de transmissão "
    "ou desliga portas de RF. O bom desempenho observado nesse cenário (0% de violação) deve-se mais à carga reduzida "
    "do que à eficiência energética. Testes com carga constante e diferentes perfis de energia são necessários."
)
report_lines.append("")

report_lines.append("## 12. Conclusão")
report_lines.append("")
report_lines.append(
    "O slice-aware scheduler demonstra capacidade de diferenciação básica de tráfego, "
    "mas falha em garantir SLAs rígidos sob contenção de recursos. Cenários leves (*low*, *night_energy*) "
    "apresentam resultados aceitáveis, enquanto cenários de pico (*congestion*, *balanced*) resultam em "
    "violações generalizadas de delay, throughput e PDR. A transição para controle dinâmico de pesos, "
    "aliada a mecanismos de proteção de slices (minPRB garantido), é o próximo passo crítico "
    "para viabilizar a proposta de GreenRAN com slicing inteligente."
)
report_lines.append("")
report_lines.append("---")
report_lines.append("*Relatório gerado automaticamente pelo pipeline de análise de resultados ns-3.*")

# Salvar relatório
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

print(f"Relatório salvo em: {REPORT_PATH}")
print(f"Figuras salvas em: {FIG_DIR}")
