import pandas as pd
from pathlib import Path
import json

scenarios = ["low_traffic", "normal", "congestion", "stressed", "insufficient_resources"]
base_rslaq = Path("/home/elioth/Documentos/artigo_jussi/ns-3-dev/results_rslaq")
base_slice = Path("/home/elioth/Documentos/artigo_jussi/ns-3-dev/results_sliceaware")

summary = []

for scen in scenarios:
    rslaq_slice = base_rslaq / f"rslaq_{scen}_slice.csv"
    slice_slice = base_slice / scen / f"slice_{scen}_slice.csv"
    
    if not rslaq_slice.exists() or not slice_slice.exists():
        continue
    
    df_r = pd.read_csv(rslaq_slice)
    df_s = pd.read_csv(slice_slice)
    
    for _, row_r in df_r.iterrows():
        slice_name = row_r["slice"]
        row_s = df_s[df_s["slice"] == slice_name].iloc[0]
        
        summary.append({
            "scenario": scen,
            "slice": slice_name,
            "metric": "throughput_mbps",
            "rslaq": row_r["throughput_mbps"],
            "sliceaware": row_s["throughput_mbps"],
            "diff_pct": ((row_r["throughput_mbps"] - row_s["throughput_mbps"]) / row_s["throughput_mbps"]) * 100
        })
        summary.append({
            "scenario": scen,
            "slice": slice_name,
            "metric": "avg_delay_ms",
            "rslaq": row_r["avg_delay_ms"],
            "sliceaware": row_s["avg_delay_ms"],
            "diff_pct": ((row_r["avg_delay_ms"] - row_s["avg_delay_ms"]) / row_s["avg_delay_ms"]) * 100
        })
        summary.append({
            "scenario": scen,
            "slice": slice_name,
            "metric": "pdr",
            "rslaq": row_r["pdr"],
            "sliceaware": row_s["pdr"],
            "diff_pct": ((row_r["pdr"] - row_s["pdr"]) / row_s["pdr"]) * 100
        })

df_summary = pd.DataFrame(summary)

print("=" * 80)
print("COMPARATIVO RSLAQ vs SLICEAWARE - METRICAS POR SLICE E CENARIO")
print("=" * 80)

for scen in scenarios:
    print(f"\n>>> CENARIO: {scen.upper()}")
    df_scen = df_summary[df_summary["scenario"] == scen]
    if df_scen.empty:
        print("  [sem dados]")
        continue
    
    pivoted = df_scen.pivot_table(
        index="slice",
        columns="metric",
        values=["rslaq", "sliceaware", "diff_pct"],
        aggfunc="first"
    )
    
    for slice_name in pivoted.index:
        print(f"  Slice: {slice_name}")
        for metric in ["throughput_mbps", "avg_delay_ms", "pdr"]:
            r = pivoted.loc[slice_name, ("rslaq", metric)]
            s = pivoted.loc[slice_name, ("sliceaware", metric)]
            d = pivoted.loc[slice_name, ("diff_pct", metric)]
            sign = "+" if d >= 0 else ""
            print(f"    {metric:20s}: RSLAQ={r:10.4f} | SliceAware={s:10.4f} | Dif={sign}{d:7.2f}%")

print("\n" + "=" * 80)
print("RESUMO ESTRATEGICO")
print("=" * 80)

for scen in scenarios:
    df_scen = df_summary[df_summary["scenario"] == scen]
    if df_scen.empty:
        continue
    
    print(f"\nCENARIO: {scen.upper()}")
    for metric in ["throughput_mbps", "avg_delay_ms", "pdr"]:
        df_m = df_scen[df_scen["metric"] == metric]
        avg_diff = df_m["diff_pct"].mean()
        sign = "+" if avg_diff >= 0 else ""
        print(f"  {metric:20s}: diferenca media = {sign}{avg_diff:.2f}%")
