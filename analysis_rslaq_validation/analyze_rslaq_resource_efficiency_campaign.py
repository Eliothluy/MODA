#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path('/home/elioth/Documentos/artigo_jussi')
CAMPAIGN = ROOT / 'ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency/20260521_162404'
DDQN_CAMPAIGN = ROOT / 'ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency/20260522_103413'
DRL_CAMPAIGNS = [CAMPAIGN, DDQN_CAMPAIGN]
OUT = ROOT / 'analysis_rslaq_validation/rslaq_sla_resource_efficiency_20260521_162404_with_ddqn_20260522_103413'
FIG = OUT / 'figures'
TAB = OUT / 'tables'
REPORT = OUT / 'REPORT_FIGURES_SLA_RESOURCE_EFFICIENCY.md'

SCENARIOS = ['low_traffic', 'normal', 'congestion', 'stressed', 'insufficient_resources']
SCENARIO_LABELS = {
    'low_traffic': 'Low traffic',
    'normal': 'Normal',
    'congestion': 'Congestion',
    'stressed': 'Stressed',
    'insufficient_resources': 'Insufficient',
}
SLICES = ['eMBB', 'URLLC', 'MTC']
SLA = {
    'low_traffic': {'eMBB': 50.0, 'URLLC': 1.0, 'MTC': 1.0},
    'normal': {'eMBB': 50.0, 'URLLC': 1.0, 'MTC': 1.0},
    'congestion': {'eMBB': 50.0, 'URLLC': 1.0, 'MTC': 1.0},
    'stressed': {'eMBB': 50.0, 'URLLC': 1.0, 'MTC': 1.0},
    'insufficient_resources': {'eMBB': 50.0, 'URLLC': 1.0, 'MTC': 1.0},
}
RSLAQ_REWARD_SLA = {
    'low_traffic': {'eMBB': 10.0, 'URLLC_buffer': 10000.0, 'MTC': 10.0},
    'normal': {'eMBB': 10.0, 'URLLC_buffer': 10000.0, 'MTC': 10.0},
    'congestion': {'eMBB': 10.0, 'URLLC_buffer': 10000.0, 'MTC': 20.0},
    'stressed': {'eMBB': 20.0, 'URLLC_buffer': 10000.0, 'MTC': 20.0},
    'insufficient_resources': {'eMBB': 20.0, 'URLLC_buffer': 10000.0, 'MTC': 20.0},
}
METHOD_ORDER = [
    'RR', 'PF', 'BCQI', 'RSLAQ-DDQN', 'SAC-RSLAQ', 'SAC-ResourceEff'
]
METHOD_COLORS = {
    'RR': '#6b7280',
    'PF': '#2563eb',
    'BCQI': '#16a34a',
    'RSLAQ-DDQN': '#dc2626',
    'SAC-RSLAQ': '#7c3aed',
    'SAC-ResourceEff': '#ea580c',
}
METHOD_MARKERS = {
    'RR': 'o', 'PF': 's', 'BCQI': '^', 'RSLAQ-DDQN': 'D', 'SAC-RSLAQ': 'P', 'SAC-ResourceEff': 'X'
}
BASELINE_LABELS = {'pure_rr': 'RR', 'pure_pf': 'PF', 'pure_bcqi': 'BCQI'}
SLICE_WEIGHTS = np.array([0.3333, 0.4000, 0.2667], dtype=float)


def ensure_dirs():
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, **kwargs)
    except Exception as exc:
        print(f'WARN read_csv {path}: {exc}')
        return pd.DataFrame()


def ci95(values: Iterable[float]) -> float:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) <= 1:
        return 0.0 if len(arr) == 1 else np.nan
    return 1.96 * arr.std(ddof=1) / math.sqrt(len(arr))


def savefig(fig: plt.Figure, name: str):
    for ext in ['png', 'pdf']:
        fig.savefig(FIG / f'{name}.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)


def apply_style():
    plt.rcParams.update({
        'font.family': 'DejaVu Sans',
        'font.size': 9,
        'axes.titlesize': 10,
        'axes.labelsize': 9,
        'legend.fontsize': 8,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.grid': True,
        'grid.alpha': 0.24,
        'grid.linewidth': 0.7,
        'figure.dpi': 120,
    })


def parse_drl_dir(name: str):
    patterns = [
        (r'^sac_paper_(.+)_seed(\d+)$', 'SAC-RSLAQ'),
        (r'^sac_resource_efficient_(.+)_seed(\d+)$', 'SAC-ResourceEff'),
        (r'^ddqn_paper_(.+)_seed(\d+)$', 'RSLAQ-DDQN'),
        (r'^ddqn_(.+)_seed(\d+)$', 'RSLAQ-DDQN'),
    ]
    for pat, method in patterns:
        m = re.match(pat, name)
        if m:
            scenario, seed = m.groups()
            if scenario in SCENARIOS:
                return method, scenario, int(seed)
    return None


def load_training() -> pd.DataFrame:
    frames = []
    for campaign in DRL_CAMPAIGNS:
        if not campaign.exists():
            continue
        for d in campaign.iterdir():
            if not d.is_dir():
                continue
            parsed = parse_drl_dir(d.name)
            if not parsed:
                continue
            method, scenario, seed = parsed
            if method == 'RSLAQ-DDQN':
                path = d / 'ddqn_training_log.csv'
            else:
                path = d / 'sac_training_log.csv'
            df = read_csv(path)
            if df.empty:
                continue
            df['method'] = method
            df['scenario'] = scenario
            df['seed'] = seed
            df['campaign'] = campaign.name
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_steps() -> pd.DataFrame:
    frames = []
    usecols = lambda c: c in {
        'seed','scenario','episode','step','algo_mode','reward_mode','slice_id','slice',
        'throughput_mbps','dTxBytes','dRxBytes','bufferBytes_mean','bufferBytes_max',
        'plr_pct','pdr_pct','dLostPackets','resourceSharePct','action_embb','action_urllc',
        'action_mtc','reward','resource_efficiency','need_allocation_match','over_allocation',
        'under_allocation','action_smoothness_penalty','resource_efficient_shaping',
        'outage_flag','soft_flag','terminated','truncated','sim_id'
    }
    for campaign in DRL_CAMPAIGNS:
        if not campaign.exists():
            continue
        for d in campaign.iterdir():
            if not d.is_dir():
                continue
            parsed = parse_drl_dir(d.name)
            if not parsed:
                continue
            method, scenario, seed = parsed
            for path in d.glob('*/step_metrics.csv'):
                df = read_csv(path, usecols=usecols)
                if df.empty:
                    continue
                df['method'] = method
                df['scenario'] = scenario
                df['seed'] = seed
                df['campaign'] = campaign.name
                df['source_file'] = str(path)
                frames.append(df)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not out.empty:
        for col in ['throughput_mbps','dTxBytes','dRxBytes','bufferBytes_mean','bufferBytes_max','plr_pct','pdr_pct','dLostPackets','resourceSharePct','action_embb','action_urllc','action_mtc','reward']:
            if col in out:
                out[col] = pd.to_numeric(out[col], errors='coerce')
    return out


def load_baseline_summary() -> pd.DataFrame:
    manifest = CAMPAIGN / 'baseline_ns3/results_rslaq_network_only/batch_manifest.csv'
    mf = read_csv(manifest)
    frames = []
    if mf.empty:
        return pd.DataFrame()
    for row in mf.itertuples(index=False):
        if str(row.status).lower() != 'ok' or row.baseline_mode not in BASELINE_LABELS:
            continue
        path = Path(row.result_dir) / 'summary.csv'
        df = read_csv(path)
        if df.empty:
            continue
        df['scenario'] = str(row.scenario)
        df['seed'] = int(row.seed)
        df['method'] = BASELINE_LABELS[str(row.baseline_mode)]
        frames.append(df)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    for col in ['throughput_mbps_mean','delay_ms_mean','pdr_pct','plr_pct','offered_load_satisfaction_pct','sla_satisfaction_pct']:
        if col in out:
            out[col] = pd.to_numeric(out[col], errors='coerce')
    return out


def normalize(v: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    v = np.maximum(np.asarray(v, dtype=float), 0.0)
    s = v.sum()
    if s <= 0:
        v = np.maximum(np.asarray(fallback, dtype=float), 0.0)
        s = v.sum()
    if s <= 0:
        return np.ones(3) / 3.0
    return v / s


def add_resource_terms(steps: pd.DataFrame) -> pd.DataFrame:
    if steps.empty:
        return pd.DataFrame()
    rows = []
    # one decision has three slice rows; use sim_id+episode+step to rebuild demand and action.
    group_cols = ['method','scenario','seed','sim_id','episode','step']
    for keys, g in steps.groupby(group_cols, dropna=False):
        method, scenario, seed, sim_id, episode, step = keys
        by_slice = {str(r.slice): r for r in g.itertuples(index=False)}
        action = np.array([
            float(g['action_embb'].iloc[0]),
            float(g['action_urllc'].iloc[0]),
            float(g['action_mtc'].iloc[0]),
        ], dtype=float)
        alloc = normalize(action, np.ones(3))
        raw_need = []
        served = []
        for sl in SLICES:
            r = by_slice.get(sl)
            if r is None:
                tx = rx = buf = lost = thr = 0.0
            else:
                tx = max(float(getattr(r, 'dTxBytes', 0.0) or 0.0), 0.0)
                rx = max(float(getattr(r, 'dRxBytes', 0.0) or 0.0), 0.0)
                buf = max(float(getattr(r, 'bufferBytes_max', 0.0) or 0.0), 0.0)
                lost = max(float(getattr(r, 'dLostPackets', 0.0) or 0.0), 0.0)
                thr = max(float(getattr(r, 'throughput_mbps', 0.0) or 0.0), 0.0)
            need = tx + buf + lost * 1500.0
            if sl == 'eMBB':
                target = RSLAQ_REWARD_SLA[scenario]['eMBB']
                if target > 0 and tx > 0 and thr < target:
                    need *= 1.0 + min((target - thr) / target, 1.0)
            elif sl == 'URLLC':
                target = RSLAQ_REWARD_SLA[scenario]['URLLC_buffer']
                need += min(buf / target, 2.0) * target if target > 0 else 0.0
            elif sl == 'MTC':
                target = RSLAQ_REWARD_SLA[scenario]['MTC']
                if target > 0 and tx > 0 and thr < target:
                    need *= 1.0 + 0.5 * min((target - thr) / target, 1.0)
            raw_need.append(max(need, 0.0))
            served.append(min(rx / tx, 1.0) if tx > 1.0 else (1.0 if need <= 1e-9 else 0.0))
        raw_need = np.array(raw_need, dtype=float)
        demand_share = normalize(raw_need, SLICE_WEIGHTS)
        need_share = normalize(0.25 * SLICE_WEIGHTS + 0.75 * demand_share, SLICE_WEIGHTS)
        distance = 0.5 * np.abs(alloc - need_share).sum()
        match = max(0.0, 1.0 - distance)
        deadband = 0.03
        over = np.maximum(alloc - need_share - deadband, 0.0).sum()
        under = np.maximum(need_share - alloc - deadband, 0.0).sum()
        served_score = float((need_share * np.array(served)).sum())
        resource_eff = match * served_score
        rows.append({
            'method': method, 'scenario': scenario, 'seed': seed, 'sim_id': sim_id,
            'episode': episode, 'step': step,
            'action_embb': action[0], 'action_urllc': action[1], 'action_mtc': action[2],
            'alloc_embb': alloc[0], 'alloc_urllc': alloc[1], 'alloc_mtc': alloc[2],
            'need_embb': need_share[0], 'need_urllc': need_share[1], 'need_mtc': need_share[2],
            'resource_efficiency_calc': resource_eff,
            'need_allocation_match_calc': match,
            'over_allocation_calc': over,
            'under_allocation_calc': under,
            'served_score': served_score,
        })
    return pd.DataFrame(rows)


def build_sla_summary(baseline: pd.DataFrame, steps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if not baseline.empty:
        for (method, scenario, seed, sl), g in baseline.groupby(['method','scenario','seed','slice']):
            if sl not in SLICES:
                continue
            rows.append({
                'method': method, 'scenario': scenario, 'seed': seed, 'slice': sl,
                'throughput_mbps': g['throughput_mbps_mean'].mean(),
                'pdr_pct': g['pdr_pct'].mean(),
                'sla_satisfaction_pct': g['sla_satisfaction_pct'].mean(),
                'sla_met': float((g['sla_satisfaction_pct'].mean() or 0) >= 100.0),
                'source': 'baseline',
            })
    if not steps.empty:
        for (method, scenario, seed, sl), g in steps.groupby(['method','scenario','seed','slice']):
            if sl not in SLICES:
                continue
            thr = float(g['throughput_mbps'].mean())
            pdr = float(g['pdr_pct'].mean())
            if sl == 'eMBB':
                sat = min(thr / SLA[scenario]['eMBB'] * 100.0, 100.0)
                active = g[g['dTxBytes'].fillna(0) > 0]
                met = 1.0 - float((active['throughput_mbps'] < SLA[scenario]['eMBB']).mean()) if len(active) else np.nan
            elif sl == 'URLLC':
                sat = min(thr / SLA[scenario]['URLLC'] * 100.0, 100.0)
                met = 1.0 - float((g['bufferBytes_max'].fillna(0) > RSLAQ_REWARD_SLA[scenario]['URLLC_buffer']).mean())
            else:
                sat = min(thr / SLA[scenario]['MTC'] * 100.0, 100.0)
                met = 1.0 - float((g['dLostPackets'].fillna(0) > 0).mean())
            rows.append({
                'method': method, 'scenario': scenario, 'seed': seed, 'slice': sl,
                'throughput_mbps': thr, 'pdr_pct': pdr, 'sla_satisfaction_pct': sat,
                'sla_met': met, 'source': 'drl',
            })
    return pd.DataFrame(rows)


def summarize_methods(sla_df: pd.DataFrame, res_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method in METHOD_ORDER:
        g = sla_df[sla_df['method'] == method]
        if g.empty:
            continue
        rg = res_df[res_df['method'] == method] if not res_df.empty else pd.DataFrame()
        rows.append({
            'method': method,
            'sla_satisfaction_mean_pct': g['sla_satisfaction_pct'].mean(),
            'sla_reliability_mean_pct': g['sla_met'].mean() * 100.0,
            'throughput_mean_mbps': g['throughput_mbps'].mean(),
            'pdr_mean_pct': g['pdr_pct'].mean(),
            'resource_efficiency': rg['resource_efficiency_calc'].mean() if not rg.empty else np.nan,
            'need_allocation_match': rg['need_allocation_match_calc'].mean() if not rg.empty else np.nan,
            'over_allocation': rg['over_allocation_calc'].mean() if not rg.empty else np.nan,
            'under_allocation': rg['under_allocation_calc'].mean() if not rg.empty else np.nan,
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        # composite only where resource terms exist. It rewards SLA and match, penalizes waste.
        out['resource_composite_score'] = (
            out['sla_reliability_mean_pct'] / 100.0 * 0.55
            + out['resource_efficiency'].fillna(0) * 0.25
            + out['need_allocation_match'].fillna(0) * 0.20
            - out['over_allocation'].fillna(0) * 0.15
        )
    return out


def plot_sla_bars(sla_df: pd.DataFrame):
    stat = sla_df.groupby(['scenario','method'], as_index=False).agg(
        mean=('sla_satisfaction_pct','mean'),
        ci=('sla_satisfaction_pct', ci95),
    )
    methods = [m for m in METHOD_ORDER if m in stat['method'].unique()]
    x = np.arange(len(SCENARIOS))
    width = min(0.11, 0.76 / max(len(methods), 1))
    fig, ax = plt.subplots(figsize=(12.5, 4.8))
    for i, method in enumerate(methods):
        g = stat[stat['method'] == method].set_index('scenario').reindex(SCENARIOS)
        offset = (i - (len(methods)-1)/2) * width
        ax.bar(x + offset, g['mean'], width, yerr=g['ci'], capsize=2,
               label=method, color=METHOD_COLORS.get(method, '#999999'), edgecolor='white', linewidth=0.5)
    ax.axhline(100, color='#111827', linestyle='--', linewidth=1.0)
    ax.set_ylim(0, 108)
    ax.set_ylabel('SLA satisfaction (%)')
    ax.set_title('SLA satisfaction por cenario - media entre slices e seeds')
    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS], rotation=18, ha='right')
    ax.legend(ncol=3, loc='lower center', bbox_to_anchor=(0.5, -0.38), frameon=False)
    savefig(fig, 'fig_sla_satisfaction_by_scenario')


def plot_reliability_heatmap(sla_df: pd.DataFrame):
    stat = sla_df.groupby(['method','slice'], as_index=False)['sla_met'].mean()
    methods = [m for m in METHOD_ORDER if m in stat['method'].unique()]
    mat = np.full((len(methods), len(SLICES)), np.nan)
    for i, method in enumerate(methods):
        for j, sl in enumerate(SLICES):
            v = stat[(stat['method'] == method) & (stat['slice'] == sl)]['sla_met']
            if not v.empty:
                mat[i, j] = float(v.iloc[0]) * 100.0
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    im = ax.imshow(mat, cmap='YlGnBu', vmin=0, vmax=100, aspect='auto')
    ax.set_xticks(np.arange(len(SLICES)))
    ax.set_xticklabels(SLICES)
    ax.set_yticks(np.arange(len(methods)))
    ax.set_yticklabels(methods)
    for i in range(len(methods)):
        for j in range(len(SLICES)):
            val = mat[i, j]
            label = 'NA' if np.isnan(val) else f'{val:.1f}%'
            ax.text(j, i, label, ha='center', va='center', color='black' if np.isnan(val) or val < 70 else 'white', fontsize=8)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('SLA reliability (%)')
    ax.set_title('Confiabilidade SLA por metodo e slice')
    savefig(fig, 'fig_sla_reliability_heatmap_by_slice')


def plot_resource_efficiency(res_df: pd.DataFrame):
    if res_df.empty:
        return
    stat = res_df.groupby(['scenario','method'], as_index=False).agg(
        eff=('resource_efficiency_calc','mean'),
        match=('need_allocation_match_calc','mean'),
        over=('over_allocation_calc','mean'),
        under=('under_allocation_calc','mean'),
    )
    methods = [m for m in ['RSLAQ-DDQN','SAC-RSLAQ','SAC-ResourceEff'] if m in stat['method'].unique()]
    fig, axes = plt.subplots(2, 2, figsize=(11.8, 8.4), sharex=True)
    metrics = [
        ('eff', 'Resource efficiency (higher is better)', 'higher'),
        ('match', 'Need-allocation match (higher is better)', 'higher'),
        ('over', 'Over-allocation (lower is better)', 'lower'),
        ('under', 'Under-allocation (lower is better)', 'lower'),
    ]
    x = np.arange(len(SCENARIOS))
    width = min(0.20, 0.72 / max(len(methods), 1))
    for ax, (metric, title, direction) in zip(axes.ravel(), metrics):
        for i, method in enumerate(methods):
            g = stat[stat['method'] == method].set_index('scenario').reindex(SCENARIOS)
            offset = (i - (len(methods)-1)/2) * width
            ax.bar(x + offset, g[metric], width, label=method,
                   color=METHOD_COLORS.get(method, '#999'), edgecolor='white', linewidth=0.5)
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS], rotation=20, ha='right')
        ax.grid(axis='y', alpha=0.24)
        if direction == 'higher':
            ax.annotate('Better', xy=(0.90, 0.88), xytext=(0.70, 0.88), xycoords='axes fraction', arrowprops={'arrowstyle':'->', 'lw':1})
        else:
            ax.annotate('Better', xy=(0.10, 0.88), xytext=(0.30, 0.88), xycoords='axes fraction', arrowprops={'arrowstyle':'->', 'lw':1})
    handles, labels = axes[0,0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc='lower center', bbox_to_anchor=(0.5, -0.02), frameon=False)
    fig.suptitle('Eficiencia de alocacao de recursos por slice - metodos DRL')
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    savefig(fig, 'fig_resource_efficiency_drl_methods')


def plot_efficiency_vs_sla(summary: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7.4, 5.5))
    for _, row in summary.iterrows():
        method = row['method']
        x = row.get('resource_efficiency')
        y = row.get('sla_reliability_mean_pct')
        if pd.isna(x):
            # place non slice-aware baselines on a small reference strip.
            x = -0.03
        ax.scatter(x, y, s=95, color=METHOD_COLORS.get(method, '#999'), marker=METHOD_MARKERS.get(method, 'o'), edgecolor='white', linewidth=0.8, label=method)
        ax.text(x + 0.008, y + 0.8, method, fontsize=8)
    ax.axvline(0, color='#9ca3af', linestyle=':', linewidth=1.0)
    ax.text(-0.055, ax.get_ylim()[0] + 3, 'No slice\nresource control', fontsize=7, color='#6b7280')
    ax.set_xlabel('Resource efficiency score')
    ax.set_ylabel('SLA reliability mean (%)')
    ax.set_title('Trade-off SLA vs eficiencia de recurso')
    ax.set_xlim(-0.07, max(0.15, np.nanmax(summary['resource_efficiency'].to_numpy(dtype=float)) + 0.06))
    ax.set_ylim(max(0, summary['sla_reliability_mean_pct'].min() - 8), 103)
    savefig(fig, 'fig_sla_vs_resource_efficiency_tradeoff')


def plot_actions_by_slice(res_df: pd.DataFrame):
    if res_df.empty:
        return
    stat = res_df.groupby('method', as_index=False).agg(
        e=('alloc_embb','mean'), u=('alloc_urllc','mean'), m=('alloc_mtc','mean'),
        ne=('need_embb','mean'), nu=('need_urllc','mean'), nm=('need_mtc','mean'),
    )
    methods = [m for m in ['RSLAQ-DDQN','SAC-RSLAQ','SAC-ResourceEff'] if m in stat['method'].unique()]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
    bottom = np.zeros(len(methods))
    colors = {'eMBB':'#2563eb','URLLC':'#dc2626','MTC':'#16a34a'}
    x = np.arange(len(methods))
    for sl, col in [('eMBB','e'), ('URLLC','u'), ('MTC','m')]:
        vals = stat.set_index('method').reindex(methods)[col].fillna(0).to_numpy() * 100
        axes[0].bar(x, vals, bottom=bottom, label=sl, color=colors[sl], edgecolor='white')
        bottom += vals
    axes[0].set_title('PRB share alocado pelo agente')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(methods, rotation=15, ha='right')
    axes[0].set_ylabel('Share (%)')
    bottom = np.zeros(len(methods))
    for sl, col in [('eMBB','ne'), ('URLLC','nu'), ('MTC','nm')]:
        vals = stat.set_index('method').reindex(methods)[col].fillna(0).to_numpy() * 100
        axes[1].bar(x, vals, bottom=bottom, label=sl, color=colors[sl], edgecolor='white')
        bottom += vals
    axes[1].set_title('Need share estimado pela demanda')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(methods, rotation=15, ha='right')
    axes[1].legend(ncol=3, loc='lower center', bbox_to_anchor=(0.5, -0.32), frameon=False)
    fig.suptitle('Alocacao media por slice vs necessidade estimada')
    fig.tight_layout(rect=(0, 0.08, 1, 0.94))
    savefig(fig, 'fig_action_share_vs_need_share')


def plot_reward_curves(training: pd.DataFrame):
    if training.empty:
        return
    methods = [m for m in ['RSLAQ-DDQN','SAC-RSLAQ','SAC-ResourceEff'] if m in training['method'].unique()]
    fig, axes = plt.subplots(3, 2, figsize=(11.5, 9.6), sharex=True)
    axes = axes.ravel()
    for ax, scenario in zip(axes, SCENARIOS):
        for method in methods:
            g = training[(training['scenario'] == scenario) & (training['method'] == method)]
            if g.empty or 'episode' not in g or 'total_reward' not in g:
                continue
            stat = g.groupby('episode')['total_reward'].agg(['mean','std','count']).reset_index()
            x = stat['episode'].to_numpy(dtype=float)
            y = stat['mean'].to_numpy(dtype=float)
            err = 1.96 * stat['std'].fillna(0).to_numpy(dtype=float) / np.sqrt(stat['count'].clip(lower=1).to_numpy(dtype=float))
            ax.plot(x, y, label=method, color=METHOD_COLORS.get(method), linewidth=1.7)
            if stat['count'].max() >= 3:
                ax.fill_between(x, y - err, y + err, color=METHOD_COLORS.get(method), alpha=0.12)
        ax.set_title(SCENARIO_LABELS[scenario])
        ax.axhline(0, color='#111827', linewidth=0.8)
        ax.grid(True, alpha=0.22)
    axes[-1].axis('off')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower right', bbox_to_anchor=(0.98, 0.07), frameon=False)
    fig.supxlabel('Episode')
    fig.supylabel('Total reward')
    fig.suptitle('Reward por episodio - SAC 20260521_162404 + DDQN 20260522_103413')
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    savefig(fig, 'fig_reward_curves_by_scenario')


def write_report(summary: pd.DataFrame, missing_methods: list[str], figures: list[str]):
    best_sla = summary.sort_values('sla_reliability_mean_pct', ascending=False).iloc[0]
    drl = summary[summary['resource_efficiency'].notna()].copy()
    best_eff = drl.sort_values('resource_composite_score', ascending=False).iloc[0] if not drl.empty else None
    baseline = summary[summary['method'].isin(['RR', 'PF', 'BCQI'])]
    drl_methods = summary[summary['method'].isin(['RSLAQ-DDQN', 'SAC-RSLAQ', 'SAC-ResourceEff'])]
    best_drl = drl_methods.sort_values('sla_reliability_mean_pct', ascending=False).iloc[0] if not drl_methods.empty else None
    lines = []
    lines.append('# Figuras comparativas - SLA e eficiencia de recursos\n')
    lines.append('Campanhas analisadas:\n')
    lines.append(f'- Baselines e SAC: `{CAMPAIGN}`')
    lines.append(f'- DDQN/RSLAQ: `{DDQN_CAMPAIGN}`\n')
    if missing_methods:
        lines.append('## Aviso sobre metodos ausentes\n')
        lines.append('Nao foram encontrados resultados nesta pasta para: ' + ', '.join(f'`{m}`' for m in missing_methods) + '. O script suporta esses metodos se os diretorios forem adicionados ao mesmo `RUN_TAG`.\n')
    lines.append('## Ranking agregado\n')
    lines.append('| Metodo | SLA reliability medio | SLA satisfaction medio | Resource efficiency | Need-match | Over-allocation | Score composto |')
    lines.append('|---|---:|---:|---:|---:|---:|---:|')
    for _, r in summary.sort_values(['sla_reliability_mean_pct','resource_composite_score'], ascending=False).iterrows():
        def f(v): return 'NA' if pd.isna(v) else f'{v:.3f}'
        lines.append(f"| {r['method']} | {r['sla_reliability_mean_pct']:.1f}% | {r['sla_satisfaction_mean_pct']:.1f}% | {f(r['resource_efficiency'])} | {f(r['need_allocation_match'])} | {f(r['over_allocation'])} | {f(r['resource_composite_score'])} |")
    lines.append('')
    lines.append('## Leitura de pesquisador\n')
    lines.append(f"- Maior cumprimento medio de SLA nesta campanha: **{best_sla['method']}** ({best_sla['sla_reliability_mean_pct']:.1f}% de reliability media).")
    if best_drl is not None:
        lines.append(f"- Melhor DRL em cumprimento de SLA: **{best_drl['method']}** ({best_drl['sla_reliability_mean_pct']:.1f}% de reliability media).")
    if best_eff is not None:
        lines.append(f"- Melhor compromisso entre SLA e uso eficiente de recursos entre metodos com controle de PRB: **{best_eff['method']}** (score composto {best_eff['resource_composite_score']:.3f}).")
    lines.append('- Baselines RR/PF/BCQI nao fazem controle explicito de PRB por slice; por isso aparecem nos graficos de SLA, mas nao recebem score direto de eficiencia de alocacao por slice.')
    lines.append('- As figuras `resource_efficiency`, `need_allocation_match`, `over_allocation` e `under_allocation` devem ser interpretadas como metricas de politica de alocacao, nao como throughput bruto.')
    lines.append('')
    if not baseline.empty and not drl_methods.empty:
        base_mean = baseline['sla_reliability_mean_pct'].mean()
        drl_mean = drl_methods['sla_reliability_mean_pct'].mean()
        lines.append('## Por que as DRLs nao superaram os baselines nesta rodada\n')
        lines.append(f"- A evidencia principal e o gap de SLA: os baselines tiveram reliability media agregada de **{base_mean:.1f}%**, enquanto as DRLs ficaram em **{drl_mean:.1f}%**. Portanto, nesta configuracao, o controle aprendido de PRB reduziu a estabilidade do atendimento de SLA em vez de melhora-la.")
        lines.append('- O problema de controle e muito dificil para o orcamento usado: cada ponto de decisao executa uma simulacao ns-3 ruidosa, com episodios curtos e terminacao por outage. Isso produz poucas transicoes uteis depois que a politica entra em estados ruins, especialmente em congestionamento e recursos insuficientes.')
        lines.append('- O baseline BCQI explora diretamente a qualidade instantanea do canal no escalonador MAC. Ja o agente DRL atua em uma camada mais grossa, escolhendo percentuais de PRB por slice e, no DDQN, tambem um scheduler discreto. Essa acao agregada nao observa nem controla a granularidade fina por UE/RBG que favorece o BCQI.')
        lines.append('- Ha desalinhamento entre recompensa e metrica final: a recompensa RSLAQ penaliza outage por limiares de eMBB, buffer URLLC e perdas MTC, enquanto a analise de SLA usa satisfacao por throughput/PDR por slice. O agente pode melhorar reward episodico sem necessariamente maximizar a metrica agregada de SLA usada no artigo.')
        lines.append('- A decomposicao P_STA limita a liberdade da politica: metade da alocacao fica presa aos pesos estaticos. Isso protege isolamento, mas tambem reduz a capacidade do agente de reagir quando a demanda real favorece outro slice.')
        lines.append('- A campanha tambem mostra sinal de acao pouco especializada: os scores de `need_allocation_match` ficam proximos entre as DRLs. Isso sugere que as politicas ainda nao aprenderam uma real adaptacao por cenario; elas tendem a operar perto de uma alocacao media, enquanto os baselines MAC continuam explorando diversidade de canal/UE.')
        lines.append('- Como interpretacao para o artigo: o resultado nao invalida a contribuicao, mas mostra que a otimizacao DRL ainda esta limitada por representacao de estado, granularidade da acao, budget de treinamento e alinhamento da recompensa com SLA. A contribuicao de eficiencia deve ser apresentada como melhora marginal de alocacao entre DRLs, nao como superacao dos baselines MAC nesta rodada.')
        lines.append('')
    lines.append('## Figuras geradas\n')
    for fig in figures:
        lines.append(f'- `{fig}.png` / `{fig}.pdf`')
    lines.append('')
    REPORT.write_text('\n'.join(lines))


def main():
    ensure_dirs()
    apply_style()
    training = load_training()
    steps = load_steps()
    baseline = load_baseline_summary()
    resource_terms = add_resource_terms(steps)
    sla_summary = build_sla_summary(baseline, steps)
    method_summary = summarize_methods(sla_summary, resource_terms)

    training.to_csv(TAB / 'training_logs_combined.csv', index=False)
    steps.to_csv(TAB / 'step_metrics_combined.csv', index=False)
    baseline.to_csv(TAB / 'baseline_summary_combined.csv', index=False)
    resource_terms.to_csv(TAB / 'resource_efficiency_terms.csv', index=False)
    sla_summary.to_csv(TAB / 'sla_summary_by_seed_slice.csv', index=False)
    method_summary.to_csv(TAB / 'method_summary.csv', index=False)

    figures = []
    plot_sla_bars(sla_summary); figures.append('fig_sla_satisfaction_by_scenario')
    plot_reliability_heatmap(sla_summary); figures.append('fig_sla_reliability_heatmap_by_slice')
    plot_resource_efficiency(resource_terms); figures.append('fig_resource_efficiency_drl_methods')
    plot_efficiency_vs_sla(method_summary); figures.append('fig_sla_vs_resource_efficiency_tradeoff')
    plot_actions_by_slice(resource_terms); figures.append('fig_action_share_vs_need_share')
    plot_reward_curves(training); figures.append('fig_reward_curves_by_scenario')

    present = set(method_summary['method']) if not method_summary.empty else set()
    missing = [m for m in ['RSLAQ-DDQN'] if m not in present]
    write_report(method_summary, missing, figures)
    print('OUT', OUT)
    print(method_summary.sort_values(['sla_reliability_mean_pct','resource_composite_score'], ascending=False).to_string(index=False))

if __name__ == '__main__':
    main()
