# Analise RSLAQ SLA + Resource Efficiency - campanha 20260603_125013

## Escopo

- Entrada: `/home/elioth/Documentos/artigo_jussi/ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency/20260603_125013`
- Saida: `/home/elioth/Documentos/artigo_jussi/analysis_rslaq_validation/rslaq_20260603_125013`
- DRL analisado: DDQN paper, DDQN resource_efficient, SAC paper, SAC resource_efficient e Predictive SAC.
- Baseline analisado: ns-3 puro com RR, PF e BCQI em `baseline_ns3/results_rslaq_network_only`.
- Para KPIs de rede em DRL, usei os ultimos 20% dos episodios de cada seed como fase final de aprendizado.
- Recompensas de modos diferentes nao foram usadas como metrica unica de QoS; o ranking principal usa KPIs comuns de rede/SLA.

## Dados carregados

- Summaries DRL: 69 execucoes.
- Episodios DRL reconstruidos de `step_metrics.csv`: 14014 episodios/simulacoes.
- Linhas baseline por slice: 225.
- Linhas comuns pontuadas por slice: 444.

### Cobertura DRL

| method | scenario | runs |
| --- | --- | --- |
| DDQN-Paper | congestion | 4 |
| DDQN-ResourceEff | congestion | 4 |
| Predictive-SAC | congestion | 3 |
| SAC-Paper | congestion | 4 |
| SAC-ResourceEff | congestion | 4 |
| DDQN-Paper | low_traffic | 5 |
| DDQN-ResourceEff | low_traffic | 5 |
| Predictive-SAC | low_traffic | 5 |
| SAC-Paper | low_traffic | 5 |
| SAC-ResourceEff | low_traffic | 5 |
| DDQN-Paper | normal | 5 |
| DDQN-ResourceEff | normal | 5 |
| Predictive-SAC | normal | 5 |
| SAC-Paper | normal | 5 |
| SAC-ResourceEff | normal | 5 |

## Ranking de QoS/SLA

| method | source | network_score_mean | network_score_ci95 | runs |
| --- | --- | --- | --- | --- |
| RR | baseline | 0.853 | 0.017 | 25 |
| BCQI | baseline | 0.851 | 0.017 | 25 |
| PF | baseline | 0.847 | 0.017 | 25 |
| SAC-ResourceEff | DRL-late-training | 0.625 | 0.061 | 14 |
| SAC-Paper | DRL-late-training | 0.617 | 0.061 | 15 |
| DDQN-Paper | DRL-late-training | 0.609 | 0.058 | 15 |
| DDQN-ResourceEff | DRL-late-training | 0.597 | 0.054 | 15 |
| Predictive-SAC | DRL-late-training | 0.427 | 0.120 | 14 |

Interpretacao: o score fica entre 0 e 1 e combina satisfacao de throughput, PDR e PLR com pesos por slice. Para URLLC em DRL, o buffer e usado como proxy de latencia quando disponivel. Para baselines, a latencia aparece separadamente porque os logs DRL nao possuem delay/jitter.

## Comparacao resource-efficient

| scenario | comparison | challenger_score | baseline_score | delta_pct |
| --- | --- | --- | --- | --- |
| low_traffic | DDQN-ResourceEff vs DDQN-Paper | 0.658 | 0.680 | -3.24 |
| low_traffic | SAC-ResourceEff vs SAC-Paper | 0.689 | 0.692 | -0.39 |
| low_traffic | Predictive-SAC vs SAC-ResourceEff | 0.608 | 0.689 | -11.75 |
| normal | DDQN-ResourceEff vs DDQN-Paper | 0.632 | 0.641 | -1.35 |
| normal | SAC-ResourceEff vs SAC-Paper | 0.645 | 0.646 | -0.17 |
| normal | Predictive-SAC vs SAC-ResourceEff | 0.405 | 0.645 | -37.16 |
| congestion | DDQN-ResourceEff vs DDQN-Paper | 0.500 | 0.507 | -1.33 |
| congestion | SAC-ResourceEff vs SAC-Paper | 0.520 | 0.512 | 1.55 |
| congestion | Predictive-SAC vs SAC-ResourceEff | 0.226 | 0.520 | -56.62 |
| stressed | DDQN-ResourceEff vs DDQN-Paper | NA | NA | NA |
| stressed | SAC-ResourceEff vs SAC-Paper | NA | NA | NA |
| stressed | Predictive-SAC vs SAC-ResourceEff | NA | NA | NA |
| insufficient_resources | DDQN-ResourceEff vs DDQN-Paper | NA | NA | NA |
| insufficient_resources | SAC-ResourceEff vs SAC-Paper | NA | NA | NA |
| insufficient_resources | Predictive-SAC vs SAC-ResourceEff | NA | NA | NA |

## Comparacao direta com baseline

| scenario | best_drl_method | best_drl_score | best_baseline_method | best_baseline_score | gap_to_best_baseline_pct | pf_baseline_score | gap_to_pf_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| low_traffic | SAC-Paper | 0.692 | PF | 0.850 | -18.539 | 0.850 | -18.539 |
| normal | SAC-Paper | 0.646 | RR | 0.825 | -21.685 | 0.816 | -20.811 |
| congestion | SAC-ResourceEff | 0.520 | BCQI | 0.859 | -39.437 | 0.847 | -38.569 |

## Aprendizado das DRLs

| method | final_avg_100_mean | final_avg_100_ci95 | best_avg_mean | steps_per_second_mean | xapp_p95_ms_mean | runs |
| --- | --- | --- | --- | --- | --- | --- |
| DDQN-ResourceEff | 13.317 | 20.682 | 13.756 | 2.983 | 0.680 | 14 |
| DDQN-Paper | 9.960 | 21.401 | 10.104 | 3.033 | 0.690 | 14 |
| Predictive-SAC | 1.351 | 0.282 | 1.405 | 48.449 | 1.911 | 13 |
| SAC-ResourceEff | -6.018 | 10.126 | -5.783 | 2.990 | 1.097 | 14 |
| SAC-Paper | -7.313 | 10.038 | -7.010 | 2.996 | 1.101 | 14 |

Nota metodologica: `final_avg_100` e comparavel dentro do mesmo reward_mode. Entre `paper` e `resource_efficient`, a comparacao cientificamente mais segura e via KPIs de rede e SLA, pois a recompensa foi redefinida.

## Baseline e QoS 3GPP

Parametros de rede do cenario usado na campanha: 1 gNB NR, UEs estaticos, 3.55 GHz, 100 MHz, numerologia mu=1, canal 3GPP UMi, trafego downlink UDP por slice. Os perfis de carga usados no simulador foram:

| scenario | slice | ues | offered_load_mbps | sla_target |
| --- | --- | --- | --- | --- |
| low_traffic | eMBB | 2 | 5.000 | 10.000 |
| low_traffic | URLLC | 2 | 1.000 | 1.000 |
| low_traffic | MTC | 6 | 2.000 | 10.000 |
| normal | eMBB | 5 | 70.000 | 10.000 |
| normal | URLLC | 5 | 1.000 | 1.000 |
| normal | MTC | 10 | 2.000 | 10.000 |
| congestion | eMBB | 15 | 100.000 | 10.000 |
| congestion | URLLC | 10 | 1.000 | 1.000 |
| congestion | MTC | 35 | 100.000 | 20.000 |
| stressed | eMBB | 8 | 100.000 | 20.000 |
| stressed | URLLC | 12 | 1.000 | 1.000 |
| stressed | MTC | 20 | 100.000 | 20.000 |
| insufficient_resources | eMBB | 20 | 100.000 | 20.000 |
| insufficient_resources | URLLC | 10 | 2.000 | 2.000 |
| insufficient_resources | MTC | 40 | 100.000 | 20.000 |

3GPP/QoS: eMBB deve priorizar throughput agregado; URLLC deve priorizar confiabilidade, baixa latencia e buffer baixo; MTC deve priorizar grande quantidade de dispositivos com baixo trafego unitario. Nesta campanha, DRL registra throughput/PDR/PLR/buffer/alocacao, mas nao registra delay/jitter, portanto os graficos de latencia 3GPP sao somente para baselines RR/PF/BCQI.

## Graficos gerados

- `01_drl_convergence_rewards.png`: Convergencia das DRLs por cenario usando reward por episodio. Status: OK.
- `02_final_reward_distribution.png`: Distribuicao do reward final por metodo e cenario. Status: OK.
- `03_qos_throughput_by_slice.png`: Throughput por slice, DRL final vs baselines. Status: OK.
- `04_qos_pdr_by_slice.png`: PDR por slice, DRL final vs baselines. Status: OK.
- `05_qos_plr_by_slice.png`: PLR por slice, DRL final vs baselines. Status: OK.
- `06_resource_efficiency_diagnostics.png`: Diagnosticos especificos da recompensa resource_efficient. Status: OK.
- `07_slice_allocation_heatmap.png`: Alocacao real de recursos por slice nas DRLs. Status: OK.
- `08_baseline_latency_3gpp_proxy.png`: Latencia p95 dos baselines em escala log. Status: OK.
- `09_network_composite_score.png`: Score composto de QoS/SLA por cenario. Status: OK.

## Principais leituras

- Melhor score medio geral: `RR` com score 0.853.
- Cenarios em que a melhor DRL supera o melhor baseline: 0 de 3.
- Comparacoes resource-efficient com ganho positivo: 1 de 9 pares avaliaveis.
- Menor delay p95 medio para URLLC nos baselines: `RR` com 16.06 ms.
- Menor latencia p95 media de decisao xApp: `DDQN-ResourceEff` com 0.680 ms.

## Limitacoes

- A comparacao DRL vs baseline usa os KPIs disponiveis em comum; delay e jitter nao existem nos `step_metrics.csv` das DRLs.
- O desempenho de rede DRL foi estimado pela fase final do treinamento, nao por uma avaliacao offline deterministica separada da politica final.
- Algumas execucoes possuem multiplos diretorios `sim_id`; o script reconstruiu episodios a partir de `step_metrics.csv` e removeu duplicacao por slice no reward.
- Os baselines cobrem tambem `stressed` e `insufficient_resources`; as DRLs desta campanha podem ter cobertura incompleta nesses cenarios dependendo dos summaries existentes.
