#!/usr/bin/env python3
"""
Gera graficos de analise dos resultados RSLAQ.
Salva todos os PNGs em results_rslaq/figures/
"""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

BASE = "/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/results_rslaq"
FIGDIR = os.path.join(BASE, "figures")
os.makedirs(FIGDIR, exist_ok=True)

SCENARIOS = ["low_traffic", "normal", "congestion", "stressed", "insufficient_resources"]
SLICES = ["eMBB", "URLLC", "MTC"]
COLORS = {"eMBB": "#2196F3", "URLLC": "#FF9800", "MTC": "#4CAF50"}

SCENARIO_LABELS = {
    "low_traffic": "Low Traffic",
    "normal": "Normal",
    "congestion": "Congestion",
    "stressed": "Stressed",
    "insufficient_resources": "Insufficient\nResources",
}

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})


def load_slice_data():
    rows = []
    for sc in SCENARIOS:
        path = os.path.join(BASE, f"rslaq_{sc}_slice.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["scenario"] = sc
            rows.append(df)
    return pd.concat(rows, ignore_index=True)


def load_ue_data():
    rows = []
    for sc in SCENARIOS:
        path = os.path.join(BASE, f"rslaq_{sc}_ue.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["scenario"] = sc
            rows.append(df)
    return pd.concat(rows, ignore_index=True)


def load_timeseries():
    path = os.path.join(BASE, "rslaq_stats_timeseries.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


def load_allocations():
    path = os.path.join(BASE, "rslaq_slice_allocations.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


def plot_throughput_by_slice(slice_df):
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(SCENARIOS))
    width = 0.22

    for i, sl in enumerate(SLICES):
        vals = []
        for sc in SCENARIOS:
            row = slice_df[(slice_df["scenario"] == sc) & (slice_df["slice"] == sl)]
            vals.append(row["throughput_mbps"].values[0] if len(row) > 0 else 0)
        bars = ax.bar(x + i * width, vals, width, label=sl, color=COLORS[sl], edgecolor="white", linewidth=0.5)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                        f"{v:.1f}", ha="center", va="bottom", fontsize=7)

    ax.set_ylabel("Throughput (Mbps)")
    ax.set_title("Throughput Agregado por Slice em Cada Cenario")
    ax.set_xticks(x + width)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS])
    ax.legend(title="Slice")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "01_throughput_por_slice.png"))
    plt.close(fig)
    print("  [OK] 01_throughput_por_slice.png")


def plot_pdr_by_slice(slice_df):
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(SCENARIOS))
    width = 0.22

    for i, sl in enumerate(SLICES):
        vals = []
        for sc in SCENARIOS:
            row = slice_df[(slice_df["scenario"] == sc) & (slice_df["slice"] == sl)]
            vals.append(row["pdr"].values[0] if len(row) > 0 else 0)
        bars = ax.bar(x + i * width, vals, width, label=sl, color=COLORS[sl], edgecolor="white", linewidth=0.5)
        for bar, v in zip(bars, vals):
            if v > 0.001:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                        f"{v:.3f}", ha="center", va="bottom", fontsize=7)

    ax.set_ylabel("Packet Delivery Ratio (PDR)")
    ax.set_title("PDR por Slice em Cada Cenario")
    ax.set_xticks(x + width)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS])
    ax.legend(title="Slice")
    ax.set_ylim(0, 1.15)
    ax.axhline(y=0.999, color="gray", linestyle="--", alpha=0.5, label="_nolegend_")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "02_pdr_por_slice.png"))
    plt.close(fig)
    print("  [OK] 02_pdr_por_slice.png")


def plot_delay_by_slice(slice_df):
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(SCENARIOS))
    width = 0.22

    for i, sl in enumerate(SLICES):
        vals = []
        for sc in SCENARIOS:
            row = slice_df[(slice_df["scenario"] == sc) & (slice_df["slice"] == sl)]
            vals.append(row["avg_delay_ms"].values[0] if len(row) > 0 else 0)
        bars = ax.bar(x + i * width, vals, width, label=sl, color=COLORS[sl], edgecolor="white", linewidth=0.5)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 30,
                        f"{v:.0f}", ha="center", va="bottom", fontsize=7)

    ax.set_ylabel("Delay Medio (ms)")
    ax.set_title("Delay Medio por Slice em Cada Cenario")
    ax.set_xticks(x + width)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS])
    ax.legend(title="Slice")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "03_delay_por_slice.png"))
    plt.close(fig)
    print("  [OK] 03_delay_por_slice.png")


def plot_ue_throughput_low_traffic(ue_df):
    fig, ax = plt.subplots(figsize=(12, 5))
    df = ue_df[ue_df["scenario"] == "low_traffic"].sort_values("ue_id")
    if df.empty:
        plt.close(fig)
        return

    colors = [COLORS[s] for s in df["slice"]]
    bars = ax.bar(df["ue_id"], df["throughput_mbps"], color=colors, edgecolor="white", linewidth=0.5)

    for bar, v in zip(bars, df["throughput_mbps"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{v:.3f}", ha="center", va="bottom", fontsize=7)

    for sl, c in COLORS.items():
        ax.plot([], [], color=c, linewidth=6, label=sl)
    ax.legend(title="Slice")

    ax.set_xlabel("UE ID")
    ax.set_ylabel("Throughput (Mbps)")
    ax.set_title("Throughput por UE — Cenario Low Traffic (Validacao)")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "04_throughput_por_ue_low_traffic.png"))
    plt.close(fig)
    print("  [OK] 04_throughput_por_ue_low_traffic.png")


def plot_timeseries_throughput(ts_df):
    if ts_df.empty:
        return

    ts_df["time_s"] = ts_df["timestamp_ms"] / 1000.0

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle("Evolucao Temporal do Throughput por Slice (Timeseries)", fontsize=13, y=0.98)

    for ax, sl in zip(axes, SLICES):
        sub = ts_df[ts_df["slice"] == sl]
        if sub.empty:
            ax.set_title(f"{sl} — sem dados")
            continue

        for ue_id in sorted(sub["ue_id"].unique()):
            ue_data = sub[sub["ue_id"] == ue_id]
            ax.plot(ue_data["time_s"], ue_data["thr_mbps"],
                    alpha=0.6, linewidth=0.8, label=f"UE {ue_id}")

        ax.set_ylabel("Throughput (Mbps)")
        ax.set_title(f"Slice {sl}")
        ax.legend(loc="upper right", fontsize=7, ncol=5)
        ax.grid(alpha=0.3)
        ax.set_axisbelow(True)

    axes[-1].set_xlabel("Tempo (s)")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(FIGDIR, "05_timeseries_throughput.png"))
    plt.close(fig)
    print("  [OK] 05_timeseries_throughput.png")


def plot_timeseries_avg_per_slice(ts_df):
    if ts_df.empty:
        return
    ts_df["time_s"] = ts_df["timestamp_ms"] / 1000.0

    fig, ax = plt.subplots(figsize=(14, 5))
    for sl in SLICES:
        sub = ts_df[ts_df["slice"] == sl]
        if sub.empty:
            continue
        avg = sub.groupby("time_s")["thr_mbps"].mean().reset_index()
        ax.plot(avg["time_s"], avg["thr_mbps"], color=COLORS[sl],
                linewidth=1.5, label=f"{sl} (media/UE)")

    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Throughput Medio por UE (Mbps)")
    ax.set_title("Evolucao Temporal — Throughput Medio por UE e Slice")
    ax.legend(title="Slice")
    ax.grid(alpha=0.3)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "06_timeseries_avg_throughput.png"))
    plt.close(fig)
    print("  [OK] 06_timeseries_avg_throughput.png")


def plot_allocations(alloc_df):
    if alloc_df.empty:
        return

    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
    fig.suptitle("Alocacao de RBGs por Slice ao Longo do Tempo", fontsize=13, y=0.98)

    slice_names = {0: "eMBB", 1: "URLLC", 2: "MTC"}
    for ax, sid in zip(axes, [0, 1, 2]):
        sub = alloc_df[alloc_df["sliceId"] == sid]
        if sub.empty:
            continue
        ax.plot(sub["timeMs"] / 1000.0, sub["budgetRbg"], linestyle="--",
                color="gray", alpha=0.7, label="Budget")
        ax.plot(sub["timeMs"] / 1000.0, sub["allocatedRbg"],
                color=COLORS[slice_names[sid]], linewidth=1, label="Alocado")
        ax.set_ylabel("RBGs")
        ax.set_title(f"Slice {sid} ({slice_names[sid]})")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3)
        ax.set_axisbelow(True)

    axes[-1].set_xlabel("Tempo (s)")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(FIGDIR, "07_alocacao_rbgs.png"))
    plt.close(fig)
    print("  [OK] 07_alocacao_rbgs.png")


def plot_packets_tx_rx(slice_df):
    fig, axes = plt.subplots(1, 5, figsize=(18, 5), sharey=True)
    fig.suptitle("Pacotes Transmitidos (TX) vs Recebidos (RX) por Slice", fontsize=13, y=1.02)

    for ax, sc in zip(axes, SCENARIOS):
        sub = slice_df[slice_df["scenario"] == sc]
        x = np.arange(len(SLICES))
        width = 0.3
        tx_vals = [sub[sub["slice"] == s]["tx_packets"].values[0] if len(sub[sub["slice"] == s]) > 0 else 0 for s in SLICES]
        rx_vals = [sub[sub["slice"] == s]["rx_packets"].values[0] if len(sub[sub["slice"] == s]) > 0 else 0 for s in SLICES]

        ax.bar(x - width / 2, tx_vals, width, label="TX", color="#E0E0E0", edgecolor="gray", linewidth=0.5)
        bars_rx = ax.bar(x + width / 2, rx_vals, width, label="RX",
                         color=[COLORS[s] for s in SLICES], edgecolor="white", linewidth=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels(SLICES, fontsize=8)
        ax.set_title(SCENARIO_LABELS[sc], fontsize=9)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x / 1000:.0f}k" if x >= 1000 else f"{x:.0f}"))

    axes[0].set_ylabel("Pacotes")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "08_packets_tx_rx.png"), bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 08_packets_tx_rx.png")


def plot_heatmap(slice_df):
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    metrics = [
        ("throughput_mbps", "Throughput (Mbps)"),
        ("pdr", "PDR"),
        ("avg_delay_ms", "Delay Medio (ms)"),
    ]

    for ax, (col, title) in zip(axes, metrics):
        data = np.zeros((len(SLICES), len(SCENARIOS)))
        for i, sl in enumerate(SLICES):
            for j, sc in enumerate(SCENARIOS):
                row = slice_df[(slice_df["scenario"] == sc) & (slice_df["slice"] == sl)]
                data[i, j] = row[col].values[0] if len(row) > 0 else 0

        im = ax.imshow(data, cmap="YlOrRd", aspect="auto")
        ax.set_xticks(range(len(SCENARIOS)))
        ax.set_xticklabels([SCENARIO_LABELS[s].replace("\n", " ") for s in SCENARIOS], rotation=30, ha="right", fontsize=8)
        ax.set_yticks(range(len(SLICES)))
        ax.set_yticklabels(SLICES)
        ax.set_title(title, fontsize=10)

        for i in range(len(SLICES)):
            for j in range(len(SCENARIOS)):
                val = data[i, j]
                fmt = f"{val:.3f}" if col == "pdr" else f"{val:.1f}"
                color = "white" if val > data.max() * 0.7 else "black"
                ax.text(j, i, fmt, ha="center", va="center", fontsize=7, color=color)

        fig.colorbar(im, ax=ax, shrink=0.8)

    fig.suptitle("Heatmap Comparativo: Slice x Cenario", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "09_heatmap_comparativo.png"), bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 09_heatmap_comparativo.png")


def plot_per_ue_all_scenarios(ue_df):
    fig, axes = plt.subplots(1, 5, figsize=(20, 5), sharey=True)
    fig.suptitle("Throughput por UE em Cada Cenario", fontsize=13, y=1.02)

    for ax, sc in zip(axes, SCENARIOS):
        sub = ue_df[ue_df["scenario"] == sc].sort_values("ue_id")
        if sub.empty:
            continue
        colors = [COLORS[s] for s in sub["slice"]]
        ax.bar(sub["ue_id"], sub["throughput_mbps"], color=colors, edgecolor="white", linewidth=0.3)
        ax.set_xlabel("UE ID", fontsize=8)
        ax.set_title(SCENARIO_LABELS[sc], fontsize=9)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)

    axes[0].set_ylabel("Throughput (Mbps)")
    for sl, c in COLORS.items():
        axes[0].plot([], [], color=c, linewidth=6, label=sl)
    axes[0].legend(title="Slice", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "10_throughput_por_ue_todos.png"), bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 10_throughput_por_ue_todos.png")


def plot_resource_share_weights():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    weights = [0.3333, 0.4000, 0.2667]
    rbgs = [17, 21, 15]

    axes[0].pie(weights, labels=SLICES, colors=[COLORS[s] for s in SLICES],
                autopct="%1.1f%%", startangle=90, textprops={"fontsize": 9})
    axes[0].set_title("Pesos Configurados (%)")

    axes[1].bar(SLICES, rbgs, color=[COLORS[s] for s in SLICES], edgecolor="white")
    for i, v in enumerate(rbgs):
        axes[1].text(i, v + 0.3, str(v), ha="center", fontsize=9)
    axes[1].set_ylabel("RBGs")
    axes[1].set_title("RBGs Alocados por Slot (total=53)")
    axes[1].grid(axis="y", alpha=0.3)
    axes[1].set_axisbelow(True)

    fig.suptitle("Particionamento Estatico de Recursos", fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "11_resource_partitioning.png"), bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 11_resource_partitioning.png")


def main():
    print("Gerando graficos RSLAQ...")
    print(f"  Lendo dados de: {BASE}")
    print(f"  Salvando em: {FIGDIR}\n")

    slice_df = load_slice_data()
    ue_df = load_ue_data()
    ts_df = load_timeseries()
    alloc_df = load_allocations()

    print("Gerando graficos:")

    plot_throughput_by_slice(slice_df)
    plot_pdr_by_slice(slice_df)
    plot_delay_by_slice(slice_df)
    plot_ue_throughput_low_traffic(ue_df)
    plot_timeseries_throughput(ts_df)
    plot_timeseries_avg_per_slice(ts_df)
    plot_allocations(alloc_df)
    plot_packets_tx_rx(slice_df)
    plot_heatmap(slice_df)
    plot_per_ue_all_scenarios(ue_df)
    plot_resource_share_weights()

    print(f"\nConcluido! {len(os.listdir(FIGDIR))} graficos salvos em {FIGDIR}")


if __name__ == "__main__":
    main()
