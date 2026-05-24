#!/usr/bin/env python3
"""
Static Slice Efficiency Analysis Report
Generates HTML report with efficiency metrics
"""

import os
import json
import pandas as pd
import numpy as np

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

    # Get the algorithm column (either from baseline scheduler_name or algorithm)
    df = df.copy()
    df["algo_name"] = df.get("algorithm", df.get("scheduler_name", "Unknown"))

    # Group by algorithm, scenario, seed, and slice
    for (algo, scenario, seed), group in df.groupby(["algo_name", "scenario", "seed"]):
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


def generate_html_report(eff_df, output_file):
    """Generate HTML report with analysis"""

    algorithms = sorted(eff_df["algorithm"].unique())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Slice Resource Efficiency Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        h3 {{
            color: #555;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .metric-card {{
            background-color: #ecf0f1;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .metric-label {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        .algorithm-section {{
            margin: 30px 0;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
        }}
        .best {{
            background-color: #d4edda !important;
            font-weight: bold;
        }}
        .worst {{
            background-color: #f8d7da !important;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Slice Resource Efficiency Analysis Report</h1>
        <p>RSLAQ NS-O-RAN-Gym Results Analysis</p>
        <p><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>Executive Summary</h2>
        <div class="metric-card">
            <div class="metric-value">{len(eff_df)} slice instances analyzed</div>
            <div class="metric-label">Total data points across all algorithms and scenarios</div>
        </div>
"""

    # Summary statistics
    for algo in algorithms:
        algo_data = eff_df[eff_df["algorithm"] == algo]
        avg_throughput = algo_data["throughput_mean"].mean()
        avg_pdr = algo_data["pdr_mean"].mean()
        avg_outage = algo_data["outage_rate"].mean() * 100

        html += f"""
        <div class="metric-card" style="border-left-color: {get_algo_color(algo)}">
            <h3>{algo}</h3>
            <div style="display: flex; gap: 30px;">
                <div>
                    <div class="metric-value">{avg_throughput:.2f} Mbps</div>
                    <div class="metric-label">Avg Throughput</div>
                </div>
                <div>
                    <div class="metric-value">{avg_pdr:.2f}%</div>
                    <div class="metric-label">Avg PDR</div>
                </div>
                <div>
                    <div class="metric-value">{avg_outage:.2f}%</div>
                    <div class="metric-label">Avg Outage Rate</div>
                </div>
            </div>
        </div>
"""

    # Detailed tables by scenario
    for scenario in SCENARIOS:
        html += f"""
        <h2>Scenario: {scenario}</h2>
        <table>
            <tr>
                <th>Algorithm</th>
                <th>Slice</th>
                <th>Throughput (Mbps)</th>
                <th>PDR (%)</th>
                <th>PLR (%)</th>
                <th>Resource Share (%)</th>
                <th>Outage Rate (%)</th>
        """

        scenario_data = eff_df[eff_df["scenario"] == scenario]

        for algo in algorithms:
            for slice_name in SLICES:
                slice_data = scenario_data[
                    (scenario_data["algorithm"] == algo) &
                    (scenario_data["slice"] == slice_name)
                ]

                if not slice_data.empty:
                    throughput = slice_data["throughput_mean"].mean()
                    pdr = slice_data["pdr_mean"].mean()
                    plr = slice_data["plr_mean"].mean()
                    resource_share = slice_data["resource_share_mean"].mean()
                    outage = slice_data["outage_rate"].mean() * 100

                    html += f"""
            <tr>
                <td>{algo}</td>
                <td>{slice_name}</td>
                <td>{throughput:.2f}</td>
                <td>{pdr:.2f}</td>
                <td>{plr:.2f}</td>
                <td>{resource_share:.2f}</td>
                <td>{outage:.2f}</td>
            </tr>
"""

        html += "</table>"

    # Comparison by slice
    html += """
        <h2>Algorithm Comparison by Slice</h2>
        <table>
            <tr>
                <th>Slice</th>
                <th>Algorithm</th>
                <th>Avg Throughput</th>
                <th>Avg PDR</th>
                <th>Avg Outage Rate</th>
                <th>Best For</th>
        </table>
"""

    # Analysis: Find best algorithm for each metric
    html += """
        <h2>Key Findings</h2>
        <ul>
"""

    # Find best throughput per algorithm
    best_throughput = {}
    for algo in algorithms:
        best_throughput[algo] = eff_df[eff_df["algorithm"] == algo]["throughput_mean"].mean()

    best_algo_throughput = max(best_throughput, key=best_throughput.get)
    html += f"    <li><strong>Best Overall Throughput:</strong> {best_algo_throughput} ({best_throughput[best_algo_throughput]:.2f} Mbps)</li>"

    # Find best PDR per algorithm
    best_pdr = {}
    for algo in algorithms:
        best_pdr[algo] = eff_df[eff_df["algorithm"] == algo]["pdr_mean"].mean()

    best_algo_pdr = max(best_pdr, key=best_pdr.get)
    html += f"    <li><strong>Best Packet Delivery Ratio:</strong> {best_algo_pdr} ({best_pdr[best_algo_pdr]:.2f}%)</li>"

    # Find lowest outage per algorithm
    lowest_outage = {}
    for algo in algorithms:
        lowest_outage[algo] = eff_df[eff_df["algorithm"] == algo]["outage_rate"].mean()

    best_algo_outage = min(lowest_outage, key=lowest_outage.get)
    html += f"    <li><strong>Lowest Outage Rate:</strong> {best_algo_outage} ({lowest_outage[best_algo_outage]*100:.2f}%)</li>"

    html += """
        </ul>

        <h2>Methodology</h2>
        <p>This report analyzes slice efficiency metrics from RSLAQ NS-O-RAN-Gym experiments:</p>
        <ul>
            <li><strong>Algorithms:</strong> SAC Paper, SAC Resource Efficient, DDQN Paper</li>
            <li><strong>Slices:</strong> eMBB, URLLC, MTC</li>
            <li><strong>Scenarios:</strong> low_traffic, normal, congestion, stressed, insufficient_resources</li>
            <li><strong>Seeds:</strong> 5 independent runs per scenario</li>
        </ul>

        <h2>Metrics Explained</h2>
        <ul>
            <li><strong>Throughput:</strong> Average data rate per slice in Mbps</li>
            <li><strong>PDR (Packet Delivery Ratio):</strong> Percentage of successfully delivered packets</li>
            <li><strong>PLR (Packet Loss Ratio):</strong> Percentage of lost packets</li>
            <li><strong>Resource Share:</strong> Percentage of total resources allocated to the slice</li>
            <li><strong>Outage Rate:</strong> Percentage of time the slice experiences service disruption</li>
        </ul>
    </div>
</body>
</html>
"""

    with open(output_file, 'w') as f:
        f.write(html)

    print(f"Report generated: {output_file}")


def get_algo_color(algo):
    """Get color for algorithm"""
    colors = {
        "SAC Paper": "#e74c3c",
        "SAC Resource Efficient": "#27ae60",
        "DDQN Paper": "#3498db",
        "RR": "#95a5a6",
        "PF": "#f39c12",
        "BCQI": "#9b59b6"
    }
    return colors.get(algo, "#7f8c8d")


if __name__ == "__main__":
    print("Loading results...")
    all_results_df = load_all_results()
    print(f"Loaded {len(all_results_df)} records")

    # Compute efficiency metrics
    eff_df = compute_slice_efficiency(all_results_df)
    print(f"Computed efficiency for {len(eff_df)} slice instances")

    # Get available algorithms and scenarios
    available_algorithms = sorted(eff_df["algorithm"].unique()) if not eff_df.empty else []

    print(f"Available algorithms: {available_algorithms}")

    # Generate report
    output_file = "/home/elioth/Documentos/artigo_jussi/analysis_rslaq_validation/slice_efficiency_report.html"
    generate_html_report(eff_df, output_file)

    # Also save CSV
    csv_file = "/home/elioth/Documentos/artigo_jussi/analysis_rslaq_validation/slice_efficiency_data.csv"
    eff_df.to_csv(csv_file, index=False)
    print(f"CSV data saved: {csv_file}")

    print("\n=== SUMMARY STATISTICS ===")
    for algo in available_algorithms:
        algo_data = eff_df[eff_df["algorithm"] == algo]
        print(f"\n{algo}:")
        print(f"  Average Throughput: {algo_data['throughput_mean'].mean():.2f} Mbps")
        print(f"  Average PDR: {algo_data['pdr_mean'].mean():.2f}%")
        print(f"  Average Outage Rate: {algo_data['outage_rate'].mean() * 100:.2f}%")