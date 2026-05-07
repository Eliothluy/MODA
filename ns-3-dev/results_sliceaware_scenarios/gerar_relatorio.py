#!/usr/bin/env python3
"""
Análise Profissional de Resultados de Simulação 5G Slice-Aware
Autor: Engenharia de Dados Senior
Data: 2026-05-06
"""

import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime

RESULTS_DIR = "/home/elioth/Documentos/artigo_jussi/ns-3-dev/results_sliceaware_scenarios"
REPORT_PATH = os.path.join(RESULTS_DIR, "relatorio_analise_slices_5g.md")

SCENARIOS = [
    "greenran_normal",
    "greenran_low",
    "greenran_balanced",
    "greenran_night_energy",
    "greenran_congestion",
    "greenran_mmtc_massive",
    "greenran_video_heavy",
]

SLICE_MAP = {
    0: "VIDEO_EMBB",
    1: "SENSOR_MMTC",
    2: "URLLC_V2X",  # se existir
}

def read_csv_if_exists(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception as e:
            return None
    return None

def format_number(x, decimals=2):
    if pd.isna(x):
        return "N/A"
    return f"{x:.{decimals}f}"

def analyze_scenario(scenario_name):
    prefix = os.path.join(RESULTS_DIR, scenario_name, f"{scenario_name}_")
    
    # Carregar arquivos disponíveis
    df_slice = read_csv_if_exists(f"{prefix}greenran_slice.csv")
    df_sla = read_csv_if_exists(f"{prefix}greenran_sla.csv")
    df_ue = read_csv_if_exists(f"{prefix}greenran_ue.csv")
    df_ue_detail = read_csv_if_exists(f"{prefix}ue_detail.csv")
    df_ue_detail_ul = read_csv_if_exists(f"{prefix}ue_detail_ul.csv")
    df_active_dl = read_csv_if_exists(f"{prefix}active_dl_diag.csv")
    df_active_ul = read_csv_if_exists(f"{prefix}active_ul_diag.csv")
    df_timeseries = read_csv_if_exists(os.path.join(RESULTS_DIR, scenario_name, "greenran_stats_timeseries.csv"))
    df_harq = read_csv_if_exists(f"{prefix}harq_tracking.csv")
    df_alloc = read_csv_if_exists(f"{prefix}slice_alloc.csv")
    df_alloc_ul = read_csv_if_exists(f"{prefix}slice_alloc_ul.csv")
    
    results = {
        "scenario": scenario_name,
        "slice": df_slice,
        "sla": df_sla,
        "ue": df_ue,
        "ue_detail": df_ue_detail,
        "ue_detail_ul": df_ue_detail_ul,
        "active_dl": df_active_dl,
        "active_ul": df_active_ul,
        "timeseries": df_timeseries,
        "harq": df_harq,
        "alloc": df_alloc,
        "alloc_ul": df_alloc_ul,
    }
    return results

def generate_report():
    scenario_results = {s: analyze_scenario(s) for s in SCENARIOS}
    
    lines = []
    lines.append("# Relatório de Análise de Simulação 5G Slice-Aware")
    lines.append("")
    lines.append(f"**Data da Análise:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Analista:** Engenharia de Dados Senior - Redes 5G")
    lines.append(f"**Diretório de Origem:** `{RESULTS_DIR}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Resumo Executivo
    lines.append("## 1. Resumo Executivo")
    lines.append("")
    lines.append("Este relatório apresenta uma análise completa dos resultados de simulação de rede 5G com suporte a Network Slicing (Slice-Aware Scheduling). Foram avaliados **7 cenários distintos**, abrangendo condições normais, congestionadas, com ênfase em vídeo (eMBB), massivo IoT (mMTC) e otimização energética.")
    lines.append("")
    
    # Tabela resumo de cenários
    lines.append("### 1.1 Cenários Avaliados")
    lines.append("")
    lines.append("| Cenário | Descrição | Arquivos Disponíveis |")
    lines.append("|---------|-----------|---------------------|")
    for s in SCENARIOS:
        r = scenario_results[s]
        available = []
        for key in ["slice", "sla", "ue_detail", "active_dl", "timeseries", "harq", "alloc"]:
            if r[key] is not None:
                available.append(key)
        desc = {
            "greenran_normal": "Cenário baseline com tráfego normal",
            "greenran_low": "Cenário de carga baixa",
            "greenran_balanced": "Cenário com balanceamento de carga",
            "greenran_night_energy": "Cenário noturno com otimização energética",
            "greenran_congestion": "Cenário de congestão de rede",
            "greenran_mmtc_massive": "Cenário massivo mMTC (IoT)",
            "greenran_video_heavy": "Cenário com alta carga de vídeo (eMBB)",
        }.get(s, s)
        lines.append(f"| {s} | {desc} | {', '.join(available)} |")
    lines.append("")
    
    # Análise por cenário
    lines.append("## 2. Análise Detalhada por Cenário")
    lines.append("")
    
    for s in SCENARIOS:
        r = scenario_results[s]
        lines.append(f"### 2.{SCENARIOS.index(s)+1} Cenário: `{s}`")
        lines.append("")
        
        # 2.1 Métricas de Slice
        if r["slice"] is not None:
            df = r["slice"]
            lines.append("#### 2.1.1 Métricas Agregadas por Slice")
            lines.append("")
            lines.append("| Slice | UEs | Dir | Throughput (Mbps) | Avg Delay (ms) | PDR | Effective PDR |")
            lines.append("|-------|-----|-----|-------------------|----------------|-----|---------------|")
            for _, row in df.iterrows():
                slice_name = row.get("slice_name", row.get("slice_id", "N/A"))
                lines.append(f"| {slice_name} | {row.get('num_ues', 'N/A')} | {row.get('direction', 'N/A')} | {format_number(row.get('throughput_mbps', 0))} | {format_number(row.get('avg_delay_ms', 0), 1)} | {format_number(row.get('pdr', 0))} | {format_number(row.get('effective_pdr', 0))} |")
            lines.append("")
            
            # Estatísticas rápidas
            total_ues = df["num_ues"].sum() if "num_ues" in df.columns else 0
            avg_thr = df["throughput_mbps"].mean() if "throughput_mbps" in df.columns else 0
            avg_delay = df["avg_delay_ms"].mean() if "avg_delay_ms" in df.columns else 0
            min_pdr = df["effective_pdr"].min() if "effective_pdr" in df.columns else 1.0
            lines.append(f"- **Total de UEs:** {total_ues}")
            lines.append(f"- **Throughput Médio Agregado:** {format_number(avg_thr)} Mbps")
            lines.append(f"- **Delay Médio Agregado:** {format_number(avg_delay, 1)} ms")
            lines.append(f"- **Menor PDR (Effective):** {format_number(min_pdr)} {'⚠️ ALERTA' if min_pdr < 0.95 else '✓ OK'}")
            lines.append("")
        else:
            lines.append("*Arquivo de métricas por slice não disponível para este cenário.*")
            lines.append("")
        
        # 2.2 SLA
        if r["sla"] is not None:
            df = r["sla"]
            lines.append("#### 2.1.2 Cumprimento de SLA")
            lines.append("")
            lines.append("| Slice | Direção | SLA Delay (ms) | Medido Delay (ms) | SLA PDR | Medido PDR | SLA Thr (Mbps) | Medido Thr (Mbps) | Violação Geral |")
            lines.append("|-------|---------|----------------|-------------------|---------|------------|----------------|-------------------|----------------|")
            for _, row in df.iterrows():
                viol = "🔴 SIM" if row.get("overall_violation", 0) == 1 else "🟢 NÃO"
                lines.append(f"| {row.get('slice', 'N/A')} | {row.get('direction', 'N/A')} | {format_number(row.get('sla_delay_ms', 0), 1)} | {format_number(row.get('measured_avg_delay_ms', 0), 1)} | {format_number(row.get('sla_pdr', 0))} | {format_number(row.get('measured_effective_pdr', 0))} | {format_number(row.get('sla_throughput_mbps', 0))} | {format_number(row.get('measured_throughput_mbps', 0))} | {viol} |")
            lines.append("")
            
            total_violations = df["overall_violation"].sum() if "overall_violation" in df.columns else 0
            total_rows = len(df)
            lines.append(f"- **Total de SLAs Violados:** {int(total_violations)} / {total_rows}")
            lines.append("")
        else:
            lines.append("*Arquivo de SLA não disponível para este cenário.*")
            lines.append("")
        
        # 2.3 Buffer MAC / Congestionamento
        lines.append("#### 2.1.3 Análise de Buffer MAC e Congestionamento")
        lines.append("")
        
        buffer_analyzed = False
        
        # Análise via active_dl_diag (dlBufferSize)
        if r["active_dl"] is not None and "dlBufferSize" in r["active_dl"].columns:
            df = r["active_dl"]
            lines.append("**Downlink Buffer (active_dl_diag.csv):**")
            lines.append("")
            buf_stats = df.groupby("sliceId")["dlBufferSize"].agg(["count", "mean", "median", "max", "std"]).reset_index()
            lines.append("| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |")
            lines.append("|----------|----------|---------------|-----------------|----------------|--------|")
            for _, row in buf_stats.iterrows():
                lines.append(f"| {int(row['sliceId'])} | {int(row['count'])} | {format_number(row['mean'], 1)} | {format_number(row['median'], 1)} | {int(row['max'])} | {format_number(row['std'], 1)} |")
            lines.append("")
            
            # Identificar congestionamento
            max_buf = df["dlBufferSize"].max()
            high_buf_threshold = 50000  # 50KB como indicativo de congestionamento
            high_buf_count = (df["dlBufferSize"] > high_buf_threshold).sum()
            high_buf_pct = 100.0 * high_buf_count / len(df) if len(df) > 0 else 0
            
            lines.append(f"- **Maior Buffer DL Registrado:** {max_buf} bytes ({max_buf/1024:.1f} KB)")
            lines.append(f"- **Amostras Acima de 50KB:** {high_buf_count} ({format_number(high_buf_pct)}%)")
            if high_buf_pct > 5:
                lines.append(f"- **⚠️ ALERTA:** Percentual significativo de amostras com buffer DL elevado, indicativo de potencial congestionamento na camada MAC.")
            else:
                lines.append(f"- **✓ OK:** Buffer DL sob controle na maioria das amostras.")
            lines.append("")
            buffer_analyzed = True
        
        # Análise via ue_detail (bufQueueSize)
        if r["ue_detail"] is not None and "bufQueueSize" in r["ue_detail"].columns:
            df = r["ue_detail"]
            lines.append("**UE Detail Buffer (ue_detail.csv - bufQueueSize):**")
            lines.append("")
            buf_stats = df.groupby("sliceId")["bufQueueSize"].agg(["count", "mean", "median", "max", "std"]).reset_index()
            lines.append("| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |")
            lines.append("|----------|----------|---------------|-----------------|----------------|--------|")
            for _, row in buf_stats.iterrows():
                lines.append(f"| {int(row['sliceId'])} | {int(row['count'])} | {format_number(row['mean'], 1)} | {format_number(row['median'], 1)} | {int(row['max'])} | {format_number(row['std'], 1)} |")
            lines.append("")
            
            max_buf = df["bufQueueSize"].max()
            high_buf_count = (df["bufQueueSize"] > 50000).sum()
            high_buf_pct = 100.0 * high_buf_count / len(df) if len(df) > 0 else 0
            lines.append(f"- **Maior Buffer Queue Registrado:** {max_buf} bytes ({max_buf/1024:.1f} KB)")
            lines.append(f"- **Amostras Acima de 50KB:** {high_buf_count} ({format_number(high_buf_pct)}%)")
            lines.append("")
            buffer_analyzed = True
        
        # Análise via timeseries (tx_bytes, plr_pct)
        if r["timeseries"] is not None:
            df = r["timeseries"]
            lines.append("**Séries Temporais (timeseries.csv):**")
            lines.append("")
            if "plr_pct" in df.columns:
                plr_stats = df.groupby("slice_id")["plr_pct"].agg(["mean", "max"]).reset_index()
                lines.append("| Slice ID | PLR Médio (%) | PLR Máximo (%) |")
                lines.append("|----------|---------------|----------------|")
                for _, row in plr_stats.iterrows():
                    lines.append(f"| {int(row['slice_id'])} | {format_number(row['mean'], 2)} | {format_number(row['max'], 2)} |")
                lines.append("")
                max_plr = df["plr_pct"].max()
                if max_plr > 10:
                    lines.append(f"- **🔴 ALERTA DE PERDA:** PLR máximo de {format_number(max_plr, 2)}% detectado, indicativo de congestão ou falha de alocação de recursos.")
                else:
                    lines.append(f"- **✓ OK:** PLR máximo de {format_number(max_plr, 2)}% dentro de limites aceitáveis.")
                lines.append("")
            
            if "thr_mbps" in df.columns:
                thr_stats = df.groupby("slice_id")["thr_mbps"].agg(["mean", "min", "max"]).reset_index()
                lines.append("| Slice ID | Throughput Médio (Mbps) | Throughput Mín (Mbps) | Throughput Máx (Mbps) |")
                lines.append("|----------|-------------------------|-----------------------|-----------------------|")
                for _, row in thr_stats.iterrows():
                    lines.append(f"| {int(row['slice_id'])} | {format_number(row['mean'], 3)} | {format_number(row['min'], 3)} | {format_number(row['max'], 3)} |")
                lines.append("")
            buffer_analyzed = True
        
        if not buffer_analyzed:
            lines.append("*Dados de buffer MAC não disponíveis para este cenário.*")
            lines.append("")
        
        # 2.4 HARQ
        if r["harq"] is not None:
            df = r["harq"]
            lines.append("#### 2.1.4 Rastreamento HARQ")
            lines.append("")
            lines.append(f"- **Total de registros HARQ:** {len(df)}")
            if "status" in df.columns:
                status_counts = df["status"].value_counts().to_dict()
                for status, count in status_counts.items():
                    lines.append(f"  - Status `{status}`: {count}")
            lines.append("")
        
        # 2.5 Alocação de Recursos
        if r["alloc"] is not None:
            df = r["alloc"]
            lines.append("#### 2.1.5 Alocação de RBGs (Downlink)")
            lines.append("")
            if "rbgAllocated" in df.columns and "sliceId" in df.columns:
                alloc_stats = df.groupby("sliceId")["rbgAllocated"].agg(["sum", "mean", "max"]).reset_index()
                lines.append("| Slice ID | Total RBGs | Média RBGs | Máx RBGs |")
                lines.append("|----------|------------|------------|----------|")
                for _, row in alloc_stats.iterrows():
                    lines.append(f"| {int(row['sliceId'])} | {int(row['sum'])} | {format_number(row['mean'], 2)} | {int(row['max'])} |")
                lines.append("")
            else:
                lines.append(f"*Estrutura da alocação: {list(df.columns)}*")
                lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # Análise Comparativa
    lines.append("## 3. Análise Comparativa entre Cenários")
    lines.append("")
    
    # Tabela comparativa de throughput e delay
    lines.append("### 3.1 Comparativo de Throughput e Delay por Cenário")
    lines.append("")
    lines.append("| Cenário | Slice | Dir | Throughput (Mbps) | Delay (ms) | PDR Efetivo | SLA Violado |")
    lines.append("|---------|-------|-----|-------------------|------------|-------------|-------------|")
    for s in SCENARIOS:
        r = scenario_results[s]
        if r["slice"] is not None:
            for _, row in r["slice"].iterrows():
                slice_name = row.get("slice_name", row.get("slice_id", "N/A"))
                sla_viol = "N/A"
                if r["sla"] is not None:
                    sla_row = r["sla"][(r["sla"]["slice"] == slice_name) & (r["sla"]["direction"] == row.get("direction", ""))]
                    if not sla_row.empty:
                        sla_viol = "SIM" if sla_row.iloc[0].get("overall_violation", 0) == 1 else "NÃO"
                lines.append(f"| {s} | {slice_name} | {row.get('direction', 'N/A')} | {format_number(row.get('throughput_mbps', 0))} | {format_number(row.get('avg_delay_ms', 0), 1)} | {format_number(row.get('effective_pdr', 0))} | {sla_viol} |")
        else:
            lines.append(f"| {s} | N/A | N/A | N/A | N/A | N/A | N/A |")
    lines.append("")
    
    # Análise de Buffer MAC / Congestionamento Consolidado
    lines.append("### 3.2 Consolidado de Buffer MAC e Indicadores de Congestionamento")
    lines.append("")
    lines.append("| Cenário | Max Buffer DL (bytes) | Max Buffer Queue (bytes) | PLR Máx (%) | Status Congestão |")
    lines.append("|---------|----------------------|--------------------------|-------------|------------------|")
    for s in SCENARIOS:
        r = scenario_results[s]
        max_buf_dl = 0
        max_buf_q = 0
        max_plr = 0
        congested = False
        
        if r["active_dl"] is not None and "dlBufferSize" in r["active_dl"].columns:
            max_buf_dl = r["active_dl"]["dlBufferSize"].max()
        if r["ue_detail"] is not None and "bufQueueSize" in r["ue_detail"].columns:
            max_buf_q = r["ue_detail"]["bufQueueSize"].max()
        if r["timeseries"] is not None and "plr_pct" in r["timeseries"].columns:
            max_plr = r["timeseries"]["plr_pct"].max()
        
        if max_buf_dl > 50000 or max_buf_q > 50000 or max_plr > 10:
            congested = True
        
        status = "🔴 CONGESTIONADO" if congested else "🟢 Normal"
        lines.append(f"| {s} | {int(max_buf_dl)} | {int(max_buf_q)} | {format_number(max_plr, 2)} | {status} |")
    lines.append("")
    
    # Conclusões e Recomendações
    lines.append("## 4. Conclusões e Recomendações")
    lines.append("")
    lines.append("### 4.1 Principais Achados")
    lines.append("")
    
    # Detectar cenários problemáticos automaticamente
    problematic = []
    for s in SCENARIOS:
        r = scenario_results[s]
        issues = []
        
        if r["sla"] is not None and "overall_violation" in r["sla"].columns:
            if r["sla"]["overall_violation"].sum() > 0:
                issues.append("SLA violado")
        
        if r["active_dl"] is not None and "dlBufferSize" in r["active_dl"].columns:
            if r["active_dl"]["dlBufferSize"].max() > 50000:
                issues.append("Buffer DL elevado")
        
        if r["timeseries"] is not None and "plr_pct" in r["timeseries"].columns:
            if r["timeseries"]["plr_pct"].max() > 10:
                issues.append("PLR crítico")
        
        if issues:
            problematic.append(f"- **{s}:** {', '.join(issues)}")
    
    if problematic:
        lines.append("Os seguintes cenários apresentaram indicadores de degradação de performance:")
        lines.append("")
        for p in problematic:
            lines.append(p)
        lines.append("")
    else:
        lines.append("Não foram detectados problemas críticos de performance nos cenários analisados.")
        lines.append("")
    
    lines.append("### 4.2 Recomendações Técnicas")
    lines.append("")
    lines.append("1. **Otimização de Buffer MAC:** Cenários com buffer DL consistentemente acima de 50KB sugerem que o scheduler slice-aware pode estar sub-alocando RBGs para determinados slices. Recomenda-se revisar os pesos de priorização (`p_j`) e a decomposição `P_STA + p_opt`.")
    lines.append("")
    lines.append("2. **Garantia de SLA:** A violação frequente de SLA de delay (especialmente no slice VIDEO_EMBB) indica que o threshold de 100ms pode ser inadequado para a carga oferecida, ou que a alocação de recursos físicos está insuficiente para o BWP configurado.")
    lines.append("")
    lines.append("3. **Balanceamento eMBB vs mMTC:** No cenário `greenran_mmtc_massive`, verificar se a política de uplink (não slice-aware, conforme convenção do projeto) está criando gargalo indireto no downlink slice-aware.")
    lines.append("")
    lines.append("4. **Monitoramento de PLR:** Perdas de pacote acima de 10% em qualquer slice devem acionar mecanismos de adaptação de MCS ou aumento de redundância HARQ.")
    lines.append("")
    lines.append("5. **Eficiência Energética:** O cenário `greenran_night_energy` deve ser avaliado com cautela: redução de potência/clock pode aumentar delay e buffer; garantir que a otimização energética não comprometa SLAs críticos (URLLC).")
    lines.append("")
    
    lines.append("## 5. Metodologia de Análise de Buffer MAC")
    lines.append("")
    lines.append("A análise de congestionamento de buffer na camada MAC foi realizada com base nos seguintes indicadores:")
    lines.append("")
    lines.append("- **`dlBufferSize` (active_dl_diag.csv):** Tamanho do buffer de downlink reportado pelo diagnóstico de UEs ativos no DL. Valores persistentemente elevados indicam acúmulo de PDUs na fila MAC.")
    lines.append("- **`bufQueueSize` (ue_detail.csv):** Tamanho da fila de buffer por UE no momento da alocação. Pico acima de 50KB foi adotado como limiar de alerta.")
    lines.append("- **`plr_pct` (timeseries.csv):** Packet Loss Ratio percentual. Valores > 10% indicam descarte ou falha de entrega, frequentemente associados a overflow de buffer ou timeout de HARQ.")
    lines.append("- **HARQ Tracking:** Análise de retransmissões e status de processos HARQ ativos.")
    lines.append("")
    lines.append("> **Nota:** O projeto utiliza comunicação IPC via semáforos POSIX e CSV a cada 10ms. A granularidade temporal dos dados permite identificar padrões de burst e saturação em escala de slot/subframe.")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("*Relatório gerado automaticamente por pipeline de análise de dados. Para dúvidas ou aprofundamento, consultar a documentação do projeto em `AGENTS.md` e os logs individuais de simulação.*")
    
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"Relatório gerado com sucesso em: {REPORT_PATH}")
    return REPORT_PATH

if __name__ == "__main__":
    generate_report()
