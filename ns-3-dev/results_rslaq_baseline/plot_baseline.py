#!/usr/bin/env python3
"""
plot_baseline.py — Figuras academicas para o artigo RSLAQ.

Gera graficos de baseline (alocacao estatica, sem DRL) a partir dos
resultados da simulacao ns-3. Estilo IEEE/LaTeX.

Figuras geradas:
  Fig.1 — Baseline: Throughput agregado + Alocacao de RBGs (timeseries)
  Fig.2 — Comparacao dos 5 cenarios: Throughput + PDR por slice
  Fig.3 — Baseline detalhada: throughput medio/UE + delay + share de recursos
  Fig.4 — Pacotes TX vs RX por cenario (evidencia de starvation do MTC)
"""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

BASE = "/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/results_rslaq"
FIGDIR = os.path.join(BASE, "figures")
os.makedirs(FIGDIR, exist_ok=True)

SCENARIOS = ["low_traffic", "normal", "congestion", "stressed", "insufficient_resources"]
SLICES = ["eMBB", "URLLC", "MTC"]
COLORS = {"eMBB": "#1f77b4", "URLLC": "#2ca02c", "MTC": "#ff7f0e"}
SLICE_MAP = {0: "eMBB", 1: "URLLC", 2: "MTC"}

SCENARIO_LABELS = {
    "low_traffic": "Low Traffic",
    "normal": "Normal",
    "congestion": "Congestion",
    "stressed": "Stressed",
    "insufficient_resources": "Insuff. Resources",
}

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({
    "font.size": 11,
    "font.family": "serif",
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.dpi": 150,
    "savefig.dpi": 300,
})


def save_fig(fig, name):
    fig.savefig(os.path.join(FIGDIR, f"{name}.png"), bbox_inches="tight")
    fig.savefig(os.path.join(FIGDIR, f"{name}.pdf"), format="pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {name}.png + .pdf")


def load_slice_all():
    rows = []
    for sc in SCENARIOS:
        p = os.path.join(BASE, f"rslaq_{sc}_slice.csv")
        if os.path.exists(p):
            df = pd.read_csv(p)
            df["scenario"] = sc
            rows.append(df)
    return pd.concat(rows, ignore_index=True)


def load_ue_all():
    rows = []
    for sc in SCENARIOS:
        p = os.path.join(BASE, f"rslaq_{sc}_ue.csv")
        if os.path.exists(p):
            df = pd.read_csv(p)
            df["scenario"] = sc
            rows.append(df)
    return pd.concat(rows, ignore_index=True)


def load_timeseries():
    p = os.path.join(BASE, "rslaq_stats_timeseries.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


def load_allocations():
    p = os.path.join(BASE, "rslaq_slice_allocations.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


# ---------------------------------------------------------------------------
# Fig.1 — Baseline principal: Throughput agregado + Alocacao RBGs
# ---------------------------------------------------------------------------
def fig1_baseline_timeseries(ts_df, alloc_df):
    if ts_df.empty or alloc_df.empty:
        print("  [SKIP] Fig.1 — timeseries/allocations vazios")
        return

    ts_df["time_s"] = ts_df["timestamp_ms"] / 1000.0
    alloc_df["time_s"] = alloc_df["timeMs"] / 1000.0

    df_thr = ts_df.groupby(["timestamp_ms", "slice"])["thr_mbps"].sum().unstack().fillna(0)
    df_thr.index = df_thr.index / 1000.0

    alloc_df["slice_name"] = alloc_df["sliceId"].map(SLICE_MAP)
    df_rbg = alloc_df.groupby(["timeMs", "slice_name"])["allocatedRbg"].mean().unstack().fillna(0)
    df_rbg.index = df_rbg.index / 1000.0

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    for sl in SLICES:
        if sl in df_thr.columns:
            ax1.plot(df_thr.index, df_thr[sl], label=sl, color=COLORS[sl], linewidth=1.8)

    ax1.set_ylabel("Throughput Agregado (Mbps)", fontweight="bold")
    ax1.set_title("Network Performance with Static Allocation (No DRL)\n"
                  "Scenario: Last Executed — Aggregated Throughput per Slice",
                  fontweight="bold", fontsize=12)
    ax1.legend(loc="upper right", framealpha=0.9)
    ax1.set_xlim(left=0.4)

    for sl in SLICES:
        if sl in df_rbg.columns:
            ax2.step(df_rbg.index, df_rbg[sl], label=sl, color=COLORS[sl],
                     linewidth=1.8, where="post")

    ax2.set_ylabel("RBGs Alocados", fontweight="bold")
    ax2.set_xlabel("Simulation Time (s)", fontweight="bold")
    ax2.set_ylim(0, 30)
    ax2.legend(loc="upper right", framealpha=0.9)

    fig.align_ylabels([ax1, ax2])
    fig.tight_layout()
    save_fig(fig, "fig1_baseline_throughput_rbg")


# ---------------------------------------------------------------------------
# Fig.2 — Comparacao dos 5 cenarios: Throughput + PDR (barras agrupadas)
# ---------------------------------------------------------------------------
def fig2_scenario_comparison(slice_df):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    x = np.arange(len(SCENARIOS))
    width = 0.22

    for i, sl in enumerate(SLICES):
        vals = []
        for sc in SCENARIOS:
            row = slice_df[(slice_df["scenario"] == sc) & (slice_df["slice"] == sl)]
            vals.append(row["throughput_mbps"].values[0] if len(row) > 0 else 0)
        bars = ax1.bar(x + i * width, vals, width, label=sl, color=COLORS[sl],
                       edgecolor="white", linewidth=0.5)
        for bar, v in zip(bars, vals):
            if v > 0.01:
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                         f"{v:.1f}", ha="center", va="bottom", fontsize=7)

    ax1.set_ylabel("Throughput (Mbps)", fontweight="bold")
    ax1.set_title("(a) Aggregate Throughput per Slice", fontweight="bold")
    ax1.set_xticks(x + width)
    ax1.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS], rotation=15, ha="right")
    ax1.legend(title="Slice")
    ax1.grid(axis="y", alpha=0.3)
    ax1.set_axisbelow(True)

    for i, sl in enumerate(SLICES):
        vals = []
        for sc in SCENARIOS:
            row = slice_df[(slice_df["scenario"] == sc) & (slice_df["slice"] == sl)]
            vals.append(row["pdr"].values[0] if len(row) > 0 else 0)
        bars = ax2.bar(x + i * width, vals, width, label=sl, color=COLORS[sl],
                       edgecolor="white", linewidth=0.5)
        for bar, v in zip(bars, vals):
            if v > 0.001:
                ypos = bar.get_height() - 0.06 if v > 0.5 else bar.get_height() + 0.02
                ax2.text(bar.get_x() + bar.get_width() / 2, ypos,
                         f"{v:.3f}", ha="center", va="bottom", fontsize=7,
                         color="white" if v > 0.5 else "black")

    ax2.set_ylabel("Packet Delivery Ratio (PDR)", fontweight="bold")
    ax2.set_title("(b) PDR per Slice", fontweight="bold")
    ax2.set_xticks(x + width)
    ax2.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS], rotation=15, ha="right")
    ax2.set_ylim(0, 1.15)
    ax2.axhline(y=0.999, color="gray", linestyle="--", alpha=0.4)
    ax2.legend(title="Slice")
    ax2.grid(axis="y", alpha=0.3)
    ax2.set_axisbelow(True)

    fig.tight_layout()
    save_fig(fig, "fig2_scenario_comparison")


# ---------------------------------------------------------------------------
# Fig.3 — Baseline detalhada: throughput medio/UE + delay + resource share
# ---------------------------------------------------------------------------
def fig3_baseline_detail(ts_df, alloc_df):
    if ts_df.empty or alloc_df.empty:
        print("  [SKIP] Fig.3 — dados insuficientes")
        return

    ts_df["time_s"] = ts_df["timestamp_ms"] / 1000.0
    alloc_df["time_s"] = alloc_df["timeMs"] / 1000.0
    alloc_df["slice_name"] = alloc_df["sliceId"].map(SLICE_MAP)

    df_avg_thr = ts_df.groupby(["timestamp_ms", "slice"])["thr_mbps"].mean().unstack().fillna(0)
    df_avg_thr.index = df_avg_thr.index / 1000.0

    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True,
                              gridspec_kw={"height_ratios": [2, 1.5, 1]})

    ax1, ax2, ax3 = axes

    for sl in SLICES:
        if sl in df_avg_thr.columns:
            ax1.plot(df_avg_thr.index, df_avg_thr[sl], label=sl,
                     color=COLORS[sl], linewidth=1.5, alpha=0.9)

    ax1.set_ylabel("Avg. Throughput per UE (Mbps)", fontweight="bold")
    ax1.set_title("Static Slice-Aware Baseline — Per-UE Metrics Over Time",
                  fontweight="bold", fontsize=12)
    ax1.legend(loc="upper right", framealpha=0.9)
    ax1.grid(alpha=0.3)

    df_rsh = ts_df.groupby(["timestamp_ms", "slice"])["rsh_pct"].mean().unstack().fillna(0)
    df_rsh.index = df_rsh.index / 1000.0
    for sl in SLICES:
        if sl in df_rsh.columns:
            ax2.plot(df_rsh.index, df_rsh[sl], label=sl, color=COLORS[sl],
                     linewidth=1.5, linestyle="--")

    ax2.set_ylabel("Resource Share (%)", fontweight="bold")
    ax2.legend(loc="upper right", framealpha=0.9)
    ax2.grid(alpha=0.3)

    df_rbg = alloc_df.groupby(["timeMs", "slice_name"])["allocatedRbg"].mean().unstack().fillna(0)
    df_rbg.index = df_rbg.index / 1000.0
    for sl in SLICES:
        if sl in df_rbg.columns:
            ax3.step(df_rbg.index, df_rbg[sl], label=sl, color=COLORS[sl],
                     linewidth=1.5, where="post")

    ax3.set_ylabel("RBGs Allocated", fontweight="bold")
    ax3.set_xlabel("Simulation Time (s)", fontweight="bold")
    ax3.set_ylim(0, 30)
    ax3.legend(loc="upper right", framealpha=0.9)
    ax3.grid(alpha=0.3)

    fig.align_ylabels(axes)
    fig.tight_layout()
    save_fig(fig, "fig3_baseline_detail")


# ---------------------------------------------------------------------------
# Fig.4 — Pacotes TX vs RX (evidencia de starvation do MTC)
# ---------------------------------------------------------------------------
def fig4_tx_rx(slice_df):
    fig, axes = plt.subplots(1, 5, figsize=(16, 4.5), sharey=True)

    for ax, sc in zip(axes, SCENARIOS):
        sub = slice_df[slice_df["scenario"] == sc].copy()
        x = np.arange(len(SLICES))
        width = 0.3

        tx = [sub[sub["slice"] == s]["tx_packets"].values[0] if len(sub[sub["slice"] == s]) > 0 else 0 for s in SLICES]
        rx = [sub[sub["slice"] == s]["rx_packets"].values[0] if len(sub[sub["slice"] == s]) > 0 else 0 for s in SLICES]

        ax.bar(x - width / 2, tx, width, label="TX", color="#bdbdbd", edgecolor="gray", linewidth=0.5)
        ax.bar(x + width / 2, rx, width, label="RX",
               color=[COLORS[s] for s in SLICES], edgecolor="white", linewidth=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels(SLICES, fontsize=9)
        ax.set_title(SCENARIO_LABELS[sc], fontsize=10, fontweight="bold")
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda val, _: f"{val / 1000:.0f}k" if val >= 1000 else f"{val:.0f}"))

    axes[0].set_ylabel("Packets", fontweight="bold")
    axes[0].legend(fontsize=9)
    fig.suptitle("TX vs RX Packets per Slice — MTC Starvation Evidence",
                 fontweight="bold", fontsize=12, y=1.02)
    fig.tight_layout()
    save_fig(fig, "fig4_tx_rx_starvation")


# ---------------------------------------------------------------------------
# Fig.5 — Heatmap academico (Slice x Cenario)
# ---------------------------------------------------------------------------
def fig5_heatmap(slice_df):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

    metrics = [
        ("throughput_mbps", "Throughput (Mbps)"),
        ("pdr", "PDR"),
        ("avg_delay_ms", "Avg. Delay (ms)"),
    ]

    sc_labels = [SCENARIO_LABELS[s].replace("\n", " ") for s in SCENARIOS]

    for ax, (col, title) in zip(axes, metrics):
        data = np.zeros((len(SLICES), len(SCENARIOS)))
        for i, sl in enumerate(SLICES):
            for j, sc in enumerate(SCENARIOS):
                row = slice_df[(slice_df["scenario"] == sc) & (slice_df["slice"] == sl)]
                data[i, j] = row[col].values[0] if len(row) > 0 else 0

        im = ax.imshow(data, cmap="YlOrRd", aspect="auto", interpolation="nearest")
        ax.set_xticks(range(len(SCENARIOS)))
        ax.set_xticklabels(sc_labels, rotation=30, ha="right", fontsize=9)
        ax.set_yticks(range(len(SLICES)))
        ax.set_yticklabels(SLICES, fontsize=10)
        ax.set_title(title, fontweight="bold", fontsize=11)

        for i in range(len(SLICES)):
            for j in range(len(SCENARIOS)):
                val = data[i, j]
                fmt = f"{val:.3f}" if col == "pdr" else f"{val:.1f}"
                clr = "white" if val > data.max() * 0.65 else "black"
                ax.text(j, i, fmt, ha="center", va="center", fontsize=8, color=clr)

        fig.colorbar(im, ax=ax, shrink=0.85)

    fig.suptitle("Slice x Scenario Heatmap — Static Allocation Baseline",
                 fontweight="bold", fontsize=12, y=1.02)
    fig.tight_layout()
    save_fig(fig, "fig5_heatmap")


# ---------------------------------------------------------------------------
# Fig.6 — Per-UE throughput: cenario low_traffic vs congestion
# ---------------------------------------------------------------------------
def fig6_per_ue_contrast(ue_df):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    for ax, sc, subtitle in [
        (ax1, "low_traffic", "(a) Low Traffic — All Slices Served"),
        (ax2, "congestion", "(b) Congestion — MTC Starvation"),
    ]:
        sub = ue_df[ue_df["scenario"] == sc].sort_values("ue_id")
        if sub.empty:
            continue
        colors = [COLORS[s] for s in sub["slice"]]
        bars = ax.bar(sub["ue_id"].astype(str), sub["throughput_mbps"],
                      color=colors, edgecolor="white", linewidth=0.3)
        ax.set_xlabel("UE ID")
        ax.set_ylabel("Throughput (Mbps)")
        ax.set_title(subtitle, fontweight="bold")
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)

    for sl, c in COLORS.items():
        ax1.plot([], [], color=c, linewidth=8, label=sl)
    ax1.legend(title="Slice", loc="upper right")

    fig.suptitle("Per-UE Throughput: Baseline Behavior Under Different Loads",
                 fontweight="bold", fontsize=12, y=1.02)
    fig.tight_layout()
    save_fig(fig, "fig6_per_ue_contrast")


# ---------------------------------------------------------------------------
# Fig.7 — Throughput por UE em todos os cenarios
# ---------------------------------------------------------------------------
def fig7_per_ue_all(ue_df):
    fig, axes = plt.subplots(1, 5, figsize=(20, 4.5), sharey=True)

    for ax, sc in zip(axes, SCENARIOS):
        sub = ue_df[ue_df["scenario"] == sc].sort_values("ue_id")
        if sub.empty:
            continue
        colors = [COLORS[s] for s in sub["slice"]]
        ax.bar(sub["ue_id"].astype(str), sub["throughput_mbps"],
               color=colors, edgecolor="white", linewidth=0.3)
        ax.set_xlabel("UE ID", fontsize=9)
        ax.set_title(SCENARIO_LABELS[sc], fontweight="bold", fontsize=10)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", rotation=45, labelsize=7)

    axes[0].set_ylabel("Throughput (Mbps)", fontweight="bold")
    for sl, c in COLORS.items():
        axes[0].plot([], [], color=c, linewidth=8, label=sl)
    axes[0].legend(title="Slice", fontsize=9, loc="upper right")

    fig.suptitle("Per-UE Throughput Across All Scenarios — Static Allocation Baseline",
                 fontweight="bold", fontsize=12, y=1.02)
    fig.tight_layout()
    save_fig(fig, "fig7_per_ue_all_scenarios")


# ===========================================================================
# Main
# ===========================================================================
def main():
    print("=" * 60)
    print("RSLAQ — Academic Plot Generation (IEEE/LaTeX style)")
    print("=" * 60)
    print(f"  Data: {BASE}")
    print(f"  Output: {FIGDIR}\n")

    slice_df = load_slice_all()
    ue_df = load_ue_all()
    ts_df = load_timeseries()
    alloc_df = load_allocations()

    print("Generating figures:")

    fig1_baseline_timeseries(ts_df, alloc_df)
    fig2_scenario_comparison(slice_df)
    fig3_baseline_detail(ts_df, alloc_df)
    fig4_tx_rx(slice_df)
    fig5_heatmap(slice_df)
    fig6_per_ue_contrast(ue_df)
    fig7_per_ue_all(ue_df)

    print(f"\nDone! {len([f for f in os.listdir(FIGDIR) if f.endswith('.png')])} "
          f"PNG + PDF pairs saved to: {FIGDIR}")


if __name__ == "__main__":
    main()
