#!/usr/bin/env python3
"""
Dashboard for Slice Resource Efficiency Analysis
Analyzes RSLAQ results from ns-o-ran-gym experiments
"""

import os
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

# Configuration
RESULTS_DIR = "/home/elioth/Documentos/artigo_jussi/ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency"
SCENARIOS = ["low_traffic", "normal", "congestion", "stressed", "insufficient_resources"]
SLICES = ["eMBB", "URLLC", "MTC"]
SLICE_IDS = [0, 1, 2]


def load_step_metrics(folder_path):
    """Load and combine step_metrics.csv files from a folder"""
    all_data = []

    if not os.path.exists(folder_path):
        return pd.DataFrame()

    for episode_folder in os.listdir(folder_path):
        episode_path = os.path.join(folder_path, episode_folder)
        if not os.path.isdir(episode_path):
            continue

        step_metrics_file = os.path.join(episode_path, "step_metrics.csv")
        if os.path.exists(step_metrics_file):
            try:
                df = pd.read_csv(step_metrics_file)
                all_data.append(df)
            except Exception as e:
                print(f"Error reading {step_metrics_file}: {e}")

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()


def load_baseline_results(results_dir):
    """Load baseline results from NS3"""
    all_data = []

    baseline_manifest = os.path.join(results_dir, "baseline_ns3/results_rslaq_network_only/batch_manifest.csv")
    if not os.path.exists(baseline_manifest):
        return pd.DataFrame()

    manifest_df = pd.read_csv(baseline_manifest)

    for _, row in manifest_df.iterrows():
        result_dir = row["result_dir"]
        scenario = row["scenario"]
        baseline_mode = row["baseline_mode"]
        seed = row["seed"]

        if baseline_mode == "pure_bcqi":
            scheduler_id = 2
            scheduler_name = "BCQI"
        elif baseline_mode == "pure_pf":
            scheduler_id = 1
            scheduler_name = "PF"
        else:  # pure_rr
            scheduler_id = 0
            scheduler_name = "RR"

        for episode_folder in os.listdir(result_dir):
            episode_path = os.path.join(result_dir, episode_folder)
            if not os.path.isdir(episode_path):
                continue

            step_metrics_file = os.path.join(episode_path, "step_metrics.csv")
            if os.path.exists(step_metrics_file):
                try:
                    df = pd.read_csv(step_metrics_file)
                    df["baseline_mode"] = baseline_mode
                    df["scheduler_name"] = scheduler_name
                    all_data.append(df)
                except Exception as e:
                    print(f"Error reading baseline {step_metrics_file}: {e}")

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()


def load_algorithm_results(run_dir, algo_name):
    """Load results from RL algorithms (SAC, DDQN)"""
    all_data = []

    if not os.path.exists(run_dir):
        return pd.DataFrame()

    # Extract scenario and seed from folder name
    parts = os.path.basename(run_dir).split("_")
    scenario = parts[2] if len(parts) > 2 else "normal"

    for episode_folder in os.listdir(run_dir):
        episode_path = os.path.join(run_dir, episode_folder)
        if not os.path.isdir(episode_path):
            continue

        step_metrics_file = os.path.join(episode_path, "step_metrics.csv")
        if os.path.exists(step_metrics_file):
            try:
                df = pd.read_csv(step_metrics_file)
                df["algorithm"] = algo_name
                all_data.append(df)
            except Exception as e:
                print(f"Error reading {algo_name} {step_metrics_file}: {e}")

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()


def load_all_results():
    """Load all experimental results"""
    all_data = []

    # Load baseline results
    baseline_dir = os.path.join(RESULTS_DIR, "20260521_162404")
    baseline_data = load_baseline_results(baseline_dir)
    if not baseline_data.empty:
        baseline_data["experiment_tag"] = "baseline"
        baseline_data["reward_mode"] = baseline_data["scheduler_name"]
        all_data.append(baseline_data)

    # Load SAC Paper results
    sac_paper_dir = os.path.join(baseline_dir)
    for seed in range(1, 6):
        for scenario in SCENARIOS:
            run_dir = os.path.join(sac_paper_dir, f"sac_paper_{scenario}_seed{seed}")
            data = load_algorithm_results(run_dir, "SAC Paper")
            if not data.empty:
                all_data.append(data)

    # Load SAC Resource Efficient results
    for seed in range(1, 6):
        for scenario in SCENARIOS:
            run_dir = os.path.join(sac_paper_dir, f"sac_resource_efficient_{scenario}_seed{seed}")
            data = load_algorithm_results(run_dir, "SAC Resource Efficient")
            if not data.empty:
                all_data.append(data)

    # Load DDQN Paper results
    ddqn_dir = os.path.join(RESULTS_DIR, "20260522_103413")
    for seed in range(1, 6):
        for scenario in SCENARIOS:
            run_dir = os.path.join(ddqn_dir, f"ddqn_paper_{scenario}_seed{seed}")
            data = load_algorithm_results(run_dir, "DDQN Paper")
            if not data.empty:
                all_data.append(data)

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()


def compute_slice_efficiency(df):
    """Compute slice efficiency metrics"""
    results = []

    if df.empty:
        return pd.DataFrame()

    # Group by algorithm, scenario, seed, and slice
    for (algo, scenario, seed), group in df.groupby(["algorithm", "scenario", "seed"]):
        for slice_id, slice_name in zip(SLICE_IDS, SLICES):
            slice_data = group[group["slice_id"] == slice_id]

            if slice_data.empty:
                continue

            # Compute metrics
            throughput = slice_data["throughput_mbps"].mean()
            throughput_std = slice_data["throughput_mbps"].std()
            pdr = slice_data["pdr_pct"].mean()
            plr = slice_data["plr_pct"].mean()
            resource_share = slice_data["resourceSharePct"].mean()
            buffer_mean = slice_data["bufferBytes_mean"].mean()

            # Outage metrics
            outage_rate = slice_data["outage_flag"].mean() if "outage_flag" in slice_data.columns else 0

            # Resource efficiency (if available)
            resource_eff = slice_data["resource_efficiency"].mean() if "resource_efficiency" in slice_data.columns else np.nan

            # Need allocation match (if available)
            need_match = slice_data["need_allocation_match"].mean() if "need_allocation_match" in slice_data.columns else np.nan

            # Reward mean
            reward = slice_data["reward"].mean() if "reward" in slice_data.columns else np.nan

            results.append({
                "algorithm": algo,
                "scenario": scenario,
                "seed": seed,
                "slice_id": slice_id,
                "slice": slice_name,
                "throughput_mean": throughput,
                "throughput_std": throughput_std,
                "pdr_mean": pdr,
                "plr_mean": plr,
                "resource_share_mean": resource_share,
                "buffer_bytes_mean": buffer_mean,
                "outage_rate": outage_rate,
                "resource_efficiency": resource_eff,
                "need_allocation_match": need_match,
                "reward": reward
            })

    return pd.DataFrame(results)


def compute_overall_metrics(eff_df):
    """Compute overall aggregated metrics"""
    if eff_df.empty:
        return pd.DataFrame()

    results = []

    for (algo, scenario), group in eff_df.groupby(["algorithm", "scenario"]):
        # Compute metrics aggregated across slices and seeds

        # Average throughput per slice
        for slice_name in SLICES:
            slice_data = group[group["slice"] == slice_name]
            if not slice_data.empty:
                results.append({
                    "algorithm": algo,
                    "scenario": scenario,
                    "metric": "throughput",
                    "slice": slice_name,
                    "value": slice_data["throughput_mean"].mean(),
                    "std": slice_data["throughput_mean"].std()
                })

        # Average PDR per slice
        for slice_name in SLICES:
            slice_data = group[group["slice"] == slice_name]
            if not slice_data.empty:
                results.append({
                    "algorithm": algo,
                    "scenario": scenario,
                    "metric": "pdr",
                    "slice": slice_name,
                    "value": slice_data["pdr_mean"].mean(),
                    "std": slice_data["pdr_mean"].std()
                })

        # Average resource efficiency
        if "resource_efficiency" in group.columns:
            valid_eff = group["resource_efficiency"].dropna()
            if not valid_eff.empty:
                results.append({
                    "algorithm": algo,
                    "scenario": scenario,
                    "metric": "resource_efficiency",
                    "slice": "overall",
                    "value": valid_eff.mean(),
                    "std": valid_eff.std()
                })

        # Outage rate
        for slice_name in SLICES:
            slice_data = group[group["slice"] == slice_name]
            if not slice_data.empty:
                results.append({
                    "algorithm": algo,
                    "scenario": scenario,
                    "metric": "outage_rate",
                    "slice": slice_name,
                    "value": slice_data["outage_rate"].mean(),
                    "std": slice_data["outage_rate"].std()
                })

    return pd.DataFrame(results)


# Load data
print("Loading results...")
all_results_df = load_all_results()
print(f"Loaded {len(all_results_df)} records")

# Compute efficiency metrics
eff_df = compute_slice_efficiency(all_results_df)
print(f"Computed efficiency for {len(eff_df)} slice instances")

# Compute overall metrics
overall_df = compute_overall_metrics(eff_df)

# Get available algorithms and scenarios
available_algorithms = sorted(eff_df["algorithm"].unique()) if not eff_df.empty else []
available_scenarios = sorted(eff_df["scenario"].unique()) if not eff_df.empty else SCENARIOS

print(f"Available algorithms: {available_algorithms}")
print(f"Available scenarios: {available_scenarios}")

# Create Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True)

# Define app layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Slice Resource Efficiency Dashboard", className="text-center mb-4"),
            html.H6("RSLAQ NS-O-RAN-Gym Results Analysis", className="text-center text-muted mb-4"),
        ], width=12)
    ]),

    # Controls
    dbc.Row([
        dbc.Col([
            dbc.Label("Scenario"),
            dcc.Dropdown(
                id="scenario-selector",
                options=[{"label": s, "value": s} for s in available_scenarios],
                value=available_scenarios[0] if available_scenarios else "normal",
                className="mb-3"
            )
        ], width=4),

        dbc.Col([
            dbc.Label("Algorithms"),
            dcc.Dropdown(
                id="algo-selector",
                options=[{"label": a, "value": a} for a in available_algorithms],
                value=available_algorithms,
                multi=True,
                className="mb-3"
            )
        ], width=4),

        dbc.Col([
            dbc.Label("Slice"),
            dcc.Dropdown(
                id="slice-selector",
                options=[{"label": s, "value": s} for s in SLICES],
                value="eMBB",
                className="mb-3"
            )
        ], width=4)
    ]),

    # Summary metrics table
    dbc.Row([
        dbc.Col([
            html.H5("Summary Metrics", className="mt-4 mb-2"),
            html.Div(id="summary-table")
        ], width=12)
    ]),

    # Charts Row 1
    dbc.Row([
        dbc.Col([
            html.H6("Throughput by Algorithm", className="mt-3"),
            dcc.Graph(id="throughput-chart")
        ], width=6),

        dbc.Col([
            html.H6("Packet Delivery Ratio (PDR)", className="mt-3"),
            dcc.Graph(id="pdr-chart")
        ], width=6)
    ]),

    # Charts Row 2
    dbc.Row([
        dbc.Col([
            html.H6("Packet Loss Ratio (PLR)", className="mt-3"),
            dcc.Graph(id="plr-chart")
        ], width=6),

        dbc.Col([
            html.H6("Resource Share", className="mt-3"),
            dcc.Graph(id="resource-chart")
        ], width=6)
    ]),

    # Charts Row 3
    dbc.Row([
        dbc.Col([
            html.H6("Outage Rate", className="mt-3"),
            dcc.Graph(id="outage-chart")
        ], width=6),

        dbc.Col([
            html.H6("Resource Efficiency", className="mt-3"),
            dcc.Graph(id="efficiency-chart")
        ], width=6)
    ]),

    # All slices comparison
    dbc.Row([
        dbc.Col([
            html.H6("All Slices Comparison - Throughput", className="mt-3"),
            dcc.Graph(id="all-slices-throughput")
        ], width=6),

        dbc.Col([
            html.H6("All Slices Comparison - PDR", className="mt-3"),
            dcc.Graph(id="all-slices-pdr")
        ], width=6)
    ]),

    # Scenario comparison
    dbc.Row([
        dbc.Col([
            html.H6("Algorithm Performance Across Scenarios", className="mt-3"),
            dcc.Graph(id="scenario-comparison")
        ], width=12)
    ]),

], fluid=True)


@app.callback(
    [Output("summary-table", "children"),
     Output("throughput-chart", "figure"),
     Output("pdr-chart", "figure"),
     Output("plr-chart", "figure"),
     Output("resource-chart", "figure"),
     Output("outage-chart", "figure"),
     Output("efficiency-chart", "figure"),
     Output("all-slices-throughput", "figure"),
     Output("all-slices-pdr", "figure"),
     Output("scenario-comparison", "figure")],
    [Input("scenario-selector", "value"),
     Input("algo-selector", "value"),
     Input("slice-selector", "value")]
)
def update_dashboard(scenario, algorithms, selected_slice):
    # Filter data
    if not algorithms:
        algorithms = available_algorithms

    filtered = eff_df[
        (eff_df["scenario"] == scenario) &
        (eff_df["algorithm"].isin(algorithms))
    ]

    if filtered.empty:
        return html.Div("No data available"), {}, {}, {}, {}, {}, {}, {}, {}, {}

    # Create summary table
    summary_data = []
    for algo in algorithms:
        algo_data = filtered[filtered["algorithm"] == algo]
        if not algo_data.empty:
            for slice_name in SLICES:
                slice_data = algo_data[algo_data["slice"] == slice_name]
                if not slice_data.empty:
                    summary_data.append({
                        "Algorithm": algo,
                        "Slice": slice_name,
                        "Throughput (Mbps)": f"{slice_data['throughput_mean'].mean():.2f} ± {slice_data['throughput_mean'].std():.2f}",
                        "PDR (%)": f"{slice_data['pdr_mean'].mean():.2f}",
                        "PLR (%)": f"{slice_data['plr_mean'].mean():.2f}",
                        "Resource Share (%)": f"{slice_data['resource_share_mean'].mean():.2f}",
                        "Outage Rate (%)": f"{slice_data['outage_rate'].mean() * 100:.2f}"
                    })

    summary_df = pd.DataFrame(summary_data)
    summary_table = dash_table.DataTable(
        data=summary_df.to_dict("records"),
        columns=[{"name": col, "id": col} for col in summary_df.columns],
        style_cell={"textAlign": "left", "padding": "10px"},
        style_header={"backgroundColor": "#007bff", "color": "white", "fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"}
        ]
    )

    # Throughput chart
    throughput_data = filtered[filtered["slice"] == selected_slice]
    throughput_fig = px.box(
        throughput_data,
        x="algorithm",
        y="throughput_mean",
        color="algorithm",
        title=f"Throughput - {selected_slice} Slice ({scenario})",
        labels={"throughput_mean": "Throughput (Mbps)", "algorithm": "Algorithm"}
    )
    throughput_fig.update_layout(showlegend=False)

    # PDR chart
    pdr_fig = px.box(
        throughput_data,
        x="algorithm",
        y="pdr_mean",
        color="algorithm",
        title=f"PDR - {selected_slice} Slice ({scenario})",
        labels={"pdr_mean": "PDR (%)", "algorithm": "Algorithm"}
    )
    pdr_fig.update_layout(showlegend=False)

    # PLR chart
    plr_fig = px.box(
        throughput_data,
        x="algorithm",
        y="plr_mean",
        color="algorithm",
        title=f"PLR - {selected_slice} Slice ({scenario})",
        labels={"plr_mean": "PLR (%)", "algorithm": "Algorithm"}
    )
    plr_fig.update_layout(showlegend=False)

    # Resource share chart
    resource_fig = px.box(
        throughput_data,
        x="algorithm",
        y="resource_share_mean",
        color="algorithm",
        title=f"Resource Share - {selected_slice} Slice ({scenario})",
        labels={"resource_share_mean": "Resource Share (%)", "algorithm": "Algorithm"}
    )
    resource_fig.update_layout(showlegend=False)

    # Outage chart
    outage_data = filtered[filtered["slice"] == selected_slice].copy()
    outage_data["outage_rate_pct"] = outage_data["outage_rate"] * 100
    outage_fig = px.box(
        outage_data,
        x="algorithm",
        y="outage_rate_pct",
        color="algorithm",
        title=f"Outage Rate - {selected_slice} Slice ({scenario})",
        labels={"outage_rate_pct": "Outage Rate (%)", "algorithm": "Algorithm"}
    )
    outage_fig.update_layout(showlegend=False)

    # Resource efficiency chart (if available)
    eff_data = filtered[filtered["slice"] == selected_slice].copy()
    eff_data = eff_data.dropna(subset=["resource_efficiency"])
    if not eff_data.empty:
        efficiency_fig = px.box(
            eff_data,
            x="algorithm",
            y="resource_efficiency",
            color="algorithm",
            title=f"Resource Efficiency - {selected_slice} Slice ({scenario})",
            labels={"resource_efficiency": "Resource Efficiency", "algorithm": "Algorithm"}
        )
        efficiency_fig.update_layout(showlegend=False)
    else:
        efficiency_fig = go.Figure()
        efficiency_fig.add_annotation(
            text="No resource efficiency data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )

    # All slices throughput comparison
    all_slices_throughput = filtered.copy()
    all_slices_throughput_fig = px.box(
        all_slices_throughput,
        x="slice",
        y="throughput_mean",
        color="algorithm",
        title=f"Throughput by Slice ({scenario})",
        labels={"throughput_mean": "Throughput (Mbps)", "slice": "Slice"}
    )

    # All slices PDR comparison
    all_slices_pdr_fig = px.box(
        all_slices_throughput,
        x="slice",
        y="pdr_mean",
        color="algorithm",
        title=f"PDR by Slice ({scenario})",
        labels={"pdr_mean": "PDR (%)", "slice": "Slice"}
    )

    # Scenario comparison (heatmap)
    if not overall_df.empty:
        scenario_comp_data = overall_df[
            (overall_df["algorithm"].isin(algorithms)) &
            (overall_df["metric"] == "throughput")
        ].copy()

        if not scenario_comp_data.empty:
            pivot_data = scenario_comp_data.pivot(
                index="algorithm",
                columns=["scenario", "slice"],
                values="value"
            )

            scenario_fig = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=[f"{s[0]}-{s[1]}" for s in pivot_data.columns],
                y=pivot_data.index,
                colorscale="Viridis",
                colorbar={"title": "Throughput (Mbps)"}
            ))
            scenario_fig.update_layout(
                title="Algorithm Performance Across All Scenarios (Throughput)",
                xaxis_title="Scenario-Slice",
                yaxis_title="Algorithm"
            )
        else:
            scenario_fig = go.Figure()
            scenario_fig.add_annotation(
                text="No scenario comparison data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
    else:
        scenario_fig = go.Figure()
        scenario_fig.add_annotation(
            text="No scenario comparison data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )

    return summary_table, throughput_fig, pdr_fig, plr_fig, resource_fig, outage_fig, efficiency_fig, all_slices_throughput_fig, all_slices_pdr_fig, scenario_fig


if __name__ == "__main__":
    print("Starting dashboard...")
    app.run(debug=True, host="0.0.0.0", port=8050)