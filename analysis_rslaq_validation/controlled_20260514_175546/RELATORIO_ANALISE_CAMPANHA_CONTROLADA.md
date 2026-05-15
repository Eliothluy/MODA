# Analise da campanha controlada RSLAQ paper_faithful
Campanha analisada: `/home/elioth/Documentos/artigo_jussi/ns-o-ran-gym/results_controlled/paper_faithful/20260514_175546`.
## Escopo
- Nenhum arquivo do ns-3 foi modificado por esta analise.
- Foram lidos apenas logs existentes da campanha controlada e baselines contidos na propria pasta.
- Saida gerada em `/home/elioth/Documentos/artigo_jussi/analysis_rslaq_validation/controlled_20260514_175546`.
## Configuracao da campanha
- `experiment_line`: `paper_faithful`
- `run_tag`: `20260514_175546`
- `scenarios`: `low_traffic normal congestion stressed insufficient_resources`
- `seeds`: `1 2 3 4 5`
- `episodes`: `50`
- `episode_steps`: `100`
- `interaction_budget`: `5000`
- `sim_time`: `1.7`
- `app_start`: `0.5`
- `period_ms`: `10`
- `p_sta_static_fraction`: `0.5`
- `p_sta_weights`: `0.3333,0.4000,0.2667`
- `reward_weights`: `0.3333,0.4000,0.2667`
## Completude dos dados
- Logs de treino: 2500 linhas; seeds por metodo/cenario: [{'method': 'RSLAQ/DDQN', 'scenario': 'congestion', 'seeds': 5}, {'method': 'RSLAQ/DDQN', 'scenario': 'insufficient_resources', 'seeds': 5}, {'method': 'RSLAQ/DDQN', 'scenario': 'low_traffic', 'seeds': 5}, {'method': 'RSLAQ/DDQN', 'scenario': 'normal', 'seeds': 5}, {'method': 'RSLAQ/DDQN', 'scenario': 'stressed', 'seeds': 5}, {'method': 'SAC', 'scenario': 'congestion', 'seeds': 5}, {'method': 'SAC', 'scenario': 'insufficient_resources', 'seeds': 5}, {'method': 'SAC', 'scenario': 'low_traffic', 'seeds': 5}, {'method': 'SAC', 'scenario': 'normal', 'seeds': 5}, {'method': 'SAC', 'scenario': 'stressed', 'seeds': 5}].
- Arquivos `step_metrics.csv`: 2500.
- Arquivos `timeseries.csv` de baseline: 100.
## Principais resultados
| method | scenario | reward_mean | rel_embb | rel_urllc | outage_embb | outage_urllc |
| --- | --- | --- | --- | --- | --- | --- |
| BCQI | congestion |  | 0.2100 |  | 0.7900 |  |
| BCQI | insufficient_resources |  | 0.0000 |  | 1.0000 |  |
| BCQI | low_traffic |  | 0.0482 |  | 0.9518 |  |
| BCQI | normal |  | 0.9900 |  | 0.0100 |  |
| BCQI | stressed |  | 0.0000 |  | 1.0000 |  |
| Opt | congestion |  | 0.5360 | 1.0000 | 0.4640 | 0.0000 |
| Opt | insufficient_resources |  | 0.0000 | 1.0000 | 1.0000 | 0.0000 |
| Opt | low_traffic |  | 0.0000 | 1.0000 | 1.0000 | 0.0000 |
| Opt | normal |  | 0.7000 | 1.0000 | 0.3000 | 0.0000 |
| Opt | stressed |  | 0.0000 | 1.0000 | 1.0000 | 0.0000 |
| PF | congestion |  | 0.1700 |  | 0.8300 |  |
| PF | insufficient_resources |  | 0.0000 |  | 1.0000 |  |
| PF | low_traffic |  | 0.0241 |  | 0.9759 |  |
| PF | normal |  | 0.9800 |  | 0.0200 |  |
| PF | stressed |  | 0.0000 |  | 1.0000 |  |
| RR | congestion |  | 0.3500 |  | 0.6500 |  |
| RR | insufficient_resources |  | 0.0000 |  | 1.0000 |  |
| RR | low_traffic |  | 0.0241 |  | 0.9759 |  |
| RR | normal |  | 0.9600 |  | 0.0400 |  |
| RR | stressed |  | 0.0100 |  | 0.9900 |  |
| RSLAQ/DDQN | congestion | 11.3312 | 0.3925 | 1.0000 | 0.6075 | 0.0000 |
| RSLAQ/DDQN | insufficient_resources | 3.9888 | 0.0000 | 1.0000 | 1.0000 | 0.0000 |
| RSLAQ/DDQN | low_traffic | 3.9788 | 0.0000 | 1.0000 | 1.0000 | 0.0000 |
| RSLAQ/DDQN | normal | 9.3568 | 0.7378 | 1.0000 | 0.2622 | 0.0000 |
| RSLAQ/DDQN | stressed | 4.0086 | 0.0008 | 1.0000 | 0.9992 | 0.0000 |
| SAC | congestion | 12.6077 | 0.4498 | 1.0000 | 0.5502 | 0.0000 |
| SAC | insufficient_resources | 1.2706 | 0.0000 | 1.0000 | 1.0000 | 0.0000 |
| SAC | low_traffic | 1.2868 | 0.0023 | 1.0000 | 0.9977 | 0.0000 |
| SAC | normal | 4.1221 | 0.7645 | 1.0000 | 0.2355 | 0.0000 |
| SAC | stressed | 1.2745 | 0.0000 | 1.0000 | 1.0000 | 0.0000 |

## Low traffic
| scenario | slice | offered_traffic_estimated_mbps | throughput_measured_mean_mbps | throughput_measured_max_mbps | sla_min | sla_soft_or_max | physical_status | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| low_traffic | eMBB | 5.0000 | 4.5814 | 12.2240 | 10.0000 | 15.0000 | erro provável de unidade/configuração | eMBB offered traffic is 5 Mbps while paper SLA minimum is 10 Mbps |
| low_traffic | URLLC | 1.0000 | 1.4376 | 5.3664 |  | 10000.0000 | factível |  |
| low_traffic | MTC | 2.0000 | 2.3896 | 5.9392 |  | 10.0000 | factível |  |

Interpretacao: no `low_traffic`, o trafego oferecido eMBB estimado e 5 Mbps, abaixo do SLA minimo paper-faithful de 10 Mbps. Portanto falha de eMBB nesse cenario deve ser tratada como incompatibilidade de unidade/configuracao ou alvo fisicamente inalinhado com a carga oferecida, nao como prova isolada de incapacidade do algoritmo.
## Reliability/outage
| method | scenario | slice | reliability_mean | reliability_std | outage_rate_mean | seeds |
| --- | --- | --- | --- | --- | --- | --- |
| BCQI | congestion | URLLC |  |  |  | 5 |
| BCQI | congestion | eMBB | 0.2100 | 0.0000 | 0.7900 | 5 |
| BCQI | insufficient_resources | URLLC |  |  |  | 5 |
| BCQI | insufficient_resources | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| BCQI | low_traffic | URLLC |  |  |  | 5 |
| BCQI | low_traffic | eMBB | 0.0482 | 0.0000 | 0.9518 | 5 |
| BCQI | normal | URLLC |  |  |  | 5 |
| BCQI | normal | eMBB | 0.9900 | 0.0000 | 0.0100 | 5 |
| BCQI | stressed | URLLC |  |  |  | 5 |
| BCQI | stressed | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| Opt | congestion | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| Opt | congestion | eMBB | 0.5360 | 0.0537 | 0.4640 | 5 |
| Opt | insufficient_resources | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| Opt | insufficient_resources | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| Opt | low_traffic | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| Opt | low_traffic | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| Opt | normal | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| Opt | normal | eMBB | 0.7000 | 0.0000 | 0.3000 | 5 |
| Opt | stressed | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| Opt | stressed | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| PF | congestion | URLLC |  |  |  | 5 |
| PF | congestion | eMBB | 0.1700 | 0.0447 | 0.8300 | 5 |
| PF | insufficient_resources | URLLC |  |  |  | 5 |
| PF | insufficient_resources | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| PF | low_traffic | URLLC |  |  |  | 5 |
| PF | low_traffic | eMBB | 0.0241 | 0.0000 | 0.9759 | 5 |
| PF | normal | URLLC |  |  |  | 5 |
| PF | normal | eMBB | 0.9800 | 0.0000 | 0.0200 | 5 |
| PF | stressed | URLLC |  |  |  | 5 |
| PF | stressed | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| RR | congestion | URLLC |  |  |  | 5 |
| RR | congestion | eMBB | 0.3500 | 0.0000 | 0.6500 | 5 |
| RR | insufficient_resources | URLLC |  |  |  | 5 |
| RR | insufficient_resources | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| RR | low_traffic | URLLC |  |  |  | 5 |
| RR | low_traffic | eMBB | 0.0241 | 0.0000 | 0.9759 | 5 |
| RR | normal | URLLC |  |  |  | 5 |
| RR | normal | eMBB | 0.9600 | 0.0000 | 0.0400 | 5 |
| RR | stressed | URLLC |  |  |  | 5 |
| RR | stressed | eMBB | 0.0100 | 0.0000 | 0.9900 | 5 |
| RSLAQ/DDQN | congestion | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| RSLAQ/DDQN | congestion | eMBB | 0.3925 | 0.0236 | 0.6075 | 5 |
| RSLAQ/DDQN | insufficient_resources | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| RSLAQ/DDQN | insufficient_resources | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| RSLAQ/DDQN | low_traffic | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| RSLAQ/DDQN | low_traffic | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| RSLAQ/DDQN | normal | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| RSLAQ/DDQN | normal | eMBB | 0.7378 | 0.0111 | 0.2622 | 5 |
| RSLAQ/DDQN | stressed | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| RSLAQ/DDQN | stressed | eMBB | 0.0008 | 0.0018 | 0.9992 | 5 |
| SAC | congestion | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| SAC | congestion | eMBB | 0.4498 | 0.0104 | 0.5502 | 5 |
| SAC | insufficient_resources | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| SAC | insufficient_resources | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |
| SAC | low_traffic | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| SAC | low_traffic | eMBB | 0.0023 | 0.0051 | 0.9977 | 5 |
| SAC | normal | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| SAC | normal | eMBB | 0.7645 | 0.0158 | 0.2355 | 5 |
| SAC | stressed | URLLC | 1.0000 | 0.0000 | 0.0000 | 5 |
| SAC | stressed | eMBB | 0.0000 | 0.0000 | 1.0000 | 5 |

## Validade cientifica
- DDQN e SAC usam o mesmo orcamento configurado da campanha (`interaction_budget=5000`), mas os steps efetivos por episodio variam por termino antecipado.
- Reward nao foi usado isoladamente como conclusao; as tabelas incluem reliability e outage por slice.
- URLLC dos baselines e calculado quando `buffer_bytes` esta presente na serie temporal; quando ausente, o valor fica `NaN` e nao foi inventado.
- `insufficient_resources` aparece em figura diagnostica separada de reliability.
## Figuras
- `figures/reward_ddqn_by_scenario.png` e `figures/reward_ddqn_by_scenario.pdf`
- `figures/reward_sac_by_scenario.png` e `figures/reward_sac_by_scenario.pdf`
- `figures/reward_ddqn_vs_sac_controlled.png` e `figures/reward_ddqn_vs_sac_controlled.pdf`
- `figures/fig6_cdf_rslaq_style.png` e `figures/fig6_cdf_rslaq_style.pdf`
- `figures/fig7_reliability_rslaq_style.png` e `figures/fig7_reliability_rslaq_style.pdf`
- `figures/fig7_reliability_rslaq_style_including_insufficient.png` e `figures/fig7_reliability_rslaq_style_including_insufficient.pdf`
