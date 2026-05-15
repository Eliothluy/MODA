# Relatorio de Validacao Cientifica RSLAQ/ns-3

## 1. Resumo executivo

Esta validacao auditou a implementacao RSLAQ existente em `ns-3-dev` e `ns-o-ran-gym` e, apos autorizacao explicita, implementou correcoes de fidelidade a partir da Fase 2. Os artefatos numericos ainda usam os resultados disponiveis, salvo quando houver `results_controlled` gerado pela nova campanha.

Parecer de implementacao: **reproducao parcial corrigida, pendente de nova campanha estatistica**. O codigo agora cobre estado 4x4, pesos, P_STA no Python, DDQN com 198 acoes e aplicacao do scheduler vindo da acao. Os resultados legados continuam nao controlados para SAC vs DDQN.

## 2. Escopo e restricoes

- Alteracao autorizada em `ns-3-dev/scratch/rslaq/rslaq-sim.cc`: a coluna `algorithm` enviada pelo Python agora seleciona RR/PF/BCQI no scheduler slice-aware.
- Alteracoes em Python: logging por step, parametros de P_STA/pesos/reward, avaliacao DDQN com 198 acoes, script de campanha controlada.
- Artefatos de analise ficam em `analysis_rslaq_validation/`.
- Comparacoes SAC vs DDQN devem ser lidas como **exploratorias nao controladas**, pois os logs existentes usam orcamentos diferentes.

## 3. Metodologia

1. Auditoria somente leitura da estrutura, codigos Python, configuracoes e resultados.
2. Leitura dos baselines em `ns-3-dev/results_rslaq_network_only`.
3. Leitura dos logs em `ns-o-ran-gym/results/*_seed1`.
4. Calculo explicito de outage e reliability: `reliability = 1 - P(k_out)`.
5. Geracao de figuras estilo artigo com as metricas disponiveis, sem inventar metricas ausentes.
6. Novo protocolo controlado disponivel em `ns-o-ran-gym/examples/run_controlled_rslaq_validation.sh`.

## 4. Auditoria de unidades e metricas

Mapa de diretorios relevantes:

- `ns-3-dev/scratch/rslaq/rslaq-sim.cc`: simulador RSLAQ C++ lido apenas para auditoria.
- `ns-3-dev/results_rslaq_network_only/`: baselines RR/PF/BCQI/slice-aware/psta.
- `ns-o-ran-gym/src/environments/`: ambiente, KPIs, action spaces, reward.
- `ns-o-ran-gym/examples/`: scripts DDQN/SAC/eval/run_all.
- `ns-o-ran-gym/results/`: logs e snapshots de treino DDQN/SAC.
- `analysis_rslaq_validation/`: artefatos desta validacao.

Arquivos de configuracao de cenario:

- `ns-o-ran-gym/src/environments/scenario_configurations/rslaq_use_case.json`
- Definicoes efetivas de trafego RSLAQ em `ns-3-dev/scratch/rslaq/rslaq-sim.cc` (somente leitura): taxas por slice e tamanhos de pacote.

Arquivos de treino:

- `ns-o-ran-gym/examples/rslaq_train_ddqn.py`
- `ns-o-ran-gym/examples/rslaq_train_sac.py`
- `ns-o-ran-gym/examples/run_all_scenarios.sh`
- `ns-o-ran-gym/examples/rslaq_eval_policy.py`

Arquivos de reward:

- `ns-o-ran-gym/src/environments/rslaq_reward.py`
- `ns-o-ran-gym/src/environments/rslaq_action_spaces.py` para P_STA e transformacao de acoes.

Metricas disponiveis:

- Throughput: `thr_mbps` baseline, `throughputMbps` DRL KPM, `throughput_mbps_mean` summary. Unidade: Mbps.
- Bytes transmitidos/recebidos: `tx_bytes_delta`, `rx_bytes_delta`, `dTxBytes`, `dRxBytes`, `rx_bytes_total`, `tx_bytes_total`. Unidade: bytes.
- Buffer: `buffer_bytes`, `bufferBytes`. Unidade: bytes, lido do scheduler DL.
- Dropped/lost: `dropped_packets_delta`, `dLostPackets`. Unidade: packets, nao bytes.
- PLR/PDR: `loss_pct_interval`, `plr`, `pdr_pct`, `plr_pct`. Unidade: porcentagem.
- PRB/resource share: `rsh_configured_pct`, `resourceSharePct`, `rsh_real_pct_mean`. Unidade: porcentagem.
- Reward/outage/soft/action: logs DDQN/SAC por episodio.
- Scheduler: baselines por `baseline_mode`; a acao DDQN inclui scheduler no Python, mas a aplicacao IPC atual usa PF fixo.

Granularidade temporal:

- Baseline `timeseries.csv`: por UE e timestamp, periodo de indicacao de 10 ms.
- Baseline `summary.csv`: media final por slice por seed/run.
- DRL `step_metrics.csv`: quando gerado pela versao corrigida, uma linha por slice/step/simulacao.
- DRL legado `rslaq-kpms.txt`: snapshot sobrescrito por episodio/simulacao, por UE no ultimo passo disponivel.
- DRL `*_training_log.csv`: por episodio.
- Seeds existentes para RSLAQ: seed 1 apenas.

## 5. Fidelidade ao artigo

| item | classificacao | evidencia |
| --- | --- | --- |
| Estado 4x4 [btx,bfs,rsh,tdp] x [slices,cell] | fiel ao artigo | rslaq_kpis.py constroi matriz 4x4 em modo paper; bfs usa bufferBytes real quando disponivel. |
| Normalizacao das features | equivalente, mas adaptado ao ns-3 | Normalizacao por caps fixos: btx=200000 bytes/10 ms, buffer=100000 bytes, tdp=1000 packets, rsh=100%. |
| Espaco de acao DDQN 198 | fiel ao artigo quando include_scheduler=True | Tabela discreta com 66 combinacoes x 3 schedulers; script DDQN habilita por padrao. |
| Uso de scheduler na acao | corrigido no codigo; requer nova campanha | rslaq-sim agora le a coluna algorithm do IPC e aplica RR/PF/BCQI por slice; resultados legados ainda sao anteriores a correcao. |
| P_STA 50/50 | fiel no Python; adaptado no ns-3 | P_STA aplicado em rslaq_action_spaces.py; C++ usa percentuais diretamente para evitar dupla aplicacao. |
| Pesos 0.3333/0.4000/0.2667 | fiel ao artigo | Constantes em reward/action_spaces; C++ baseline usa 0.33/0.40/0.27. |
| SLAs por cenario | parcialmente fiel | Reward define min/soft eMBB e buffer URLLC; MTC e no-policy para outage, embora haja mtc_target para graficos/reward. |
| Funcao de recompensa | equivalente, mas adaptado ao ns-3 | h1/h2/h3 e custo scheduler implementados; outage usa confirmacao consecutiva de 5 passos. |
| Terminal por outage | equivalente, mas adaptado ao ns-3 | Hard outage termina apos warmup e streak consecutivo. |
| Terminal por soft SLA | fiel ao artigo conforme codigo | Soft eMBB gera reward 0 e termina apos warmup. |
| Reliability = 1 - P(k_out) | calculado nesta validacao | Tabelas outage_by_seed.csv e reliability_by_seed.csv. |
| insufficient_resources | equivalente como diagnostico | Incluido em treino e CDF; excluido da Fig. 7 principal e incluido em versao diagnostica. |
| SAC continuo com softmax/soma 1 | fiel/adaptado | Ator tanh -> continuous_action_to_prb usa softmax e P_STA. |
| SAC escolhe scheduler | divergente | SAC envia apenas 3 dimensoes de PRB; scheduler no C++ IPC fica PF. |
| Mesmo orcamento SAC vs DDQN | corrigido no protocolo; nao rerrodado aqui | Novo run_controlled_rslaq_validation.sh usa mesmo numero de episodios e steps por episodio para DDQN e SAC. |

## 6. Resultados por cenario

Resumo de treino DDQN:

| scenario | episodes | steps_total |
| --- | --- | --- |
| low_traffic | 50 | 270 |
| normal | 50 | 466 |
| congestion | 50 | 694 |
| stressed | 50 | 250 |
| insufficient_resources | 50 | 250 |

Resumo de treino SAC:

| scenario | episodes | steps_total |
| --- | --- | --- |
| low_traffic | 300 | 1525 |
| normal | 300 | 1.009e+04 |
| congestion | 300 | 1.204e+04 |
| stressed | 300 | 1500 |
| insufficient_resources | 300 | 1500 |

Resumo principal de reliability:

| method | scenario | seed | slice | samples | outage_probability | reliability |
| --- | --- | --- | --- | --- | --- | --- |
| RR | low_traffic | 1 | eMBB | 958 | 0.8163 | 0.1837 |
| RR | low_traffic | 1 | URLLC | 959 | 0 | 1 |
| PF | low_traffic | 1 | eMBB | 958 | 0.7933 | 0.2067 |
| PF | low_traffic | 1 | URLLC | 959 | 0 | 1 |
| BCQI | low_traffic | 1 | eMBB | 958 | 0.7704 | 0.2296 |
| BCQI | low_traffic | 1 | URLLC | 959 | 0 | 1 |
| Opt | low_traffic | 1 | eMBB | 958 | 0.8173 | 0.1827 |
| Opt | low_traffic | 1 | URLLC | 959 | 0 | 1 |
| RSLAQ/DDQN | low_traffic | 1 | eMBB | 50 | 1 | 0 |
| RSLAQ/DDQN | low_traffic | 1 | URLLC | 50 | 0 | 1 |
| SAC | low_traffic | 1 | eMBB | 300 | 1 | 0 |
| SAC | low_traffic | 1 | URLLC | 300 | 0 | 1 |
| RR | normal | 1 | eMBB | 959 | 0.005214 | 0.9948 |
| RR | normal | 1 | URLLC | 959 | 0 | 1 |
| PF | normal | 1 | eMBB | 959 | 0.006257 | 0.9937 |
| PF | normal | 1 | URLLC | 959 | 0 | 1 |
| BCQI | normal | 1 | eMBB | 959 | 0.002086 | 0.9979 |
| BCQI | normal | 1 | URLLC | 959 | 0 | 1 |
| Opt | normal | 1 | eMBB | 959 | 0.2795 | 0.7205 |
| Opt | normal | 1 | URLLC | 959 | 0 | 1 |
| RSLAQ/DDQN | normal | 1 | eMBB | 50 | 0 | 1 |
| RSLAQ/DDQN | normal | 1 | URLLC | 50 | 0 | 1 |
| SAC | normal | 1 | eMBB | 300 | 0.1333 | 0.8667 |
| SAC | normal | 1 | URLLC | 300 | 0 | 1 |
| RR | congestion | 1 | eMBB | 959 | 0.6298 | 0.3702 |
| RR | congestion | 1 | URLLC | 959 | 0 | 1 |
| PF | congestion | 1 | eMBB | 959 | 0.9426 | 0.05735 |
| PF | congestion | 1 | URLLC | 959 | 0 | 1 |
| BCQI | congestion | 1 | eMBB | 959 | 0.7456 | 0.2544 |
| BCQI | congestion | 1 | URLLC | 959 | 0 | 1 |
| Opt | congestion | 1 | eMBB | 959 | 0.4411 | 0.5589 |
| Opt | congestion | 1 | URLLC | 959 | 0 | 1 |
| RSLAQ/DDQN | congestion | 1 | eMBB | 50 | 0.58 | 0.42 |
| RSLAQ/DDQN | congestion | 1 | URLLC | 50 | 0 | 1 |
| SAC | congestion | 1 | eMBB | 300 | 0.7533 | 0.2467 |
| SAC | congestion | 1 | URLLC | 300 | 0 | 1 |
| RR | stressed | 1 | eMBB | 959 | 0.9771 | 0.02294 |
| RR | stressed | 1 | URLLC | 959 | 0 | 1 |
| PF | stressed | 1 | eMBB | 959 | 0.9802 | 0.01981 |
| PF | stressed | 1 | URLLC | 959 | 0 | 1 |

## 7. Comparacao baseline vs DDQN vs SAC

Os baselines RR/PF/BCQI/Opt legados usam uma seed/run de ns-3 e nao tem reward DRL. DDQN e SAC legados tem logs por episodio, mas somente seed 1. A comparacao SAC vs DDQN existente **nao e controlada**. O novo script `run_controlled_rslaq_validation.sh` corrige esse protocolo, mas os resultados estatisticos so passam a ser conclusivos apos a campanha multi-seed.

## 8. Figuras reproduzidas no estilo do artigo

Geradas:

- `figures/reward_ddqn_by_scenario.png` e `.pdf`
- `figures/reward_sac_by_scenario.png` e `.pdf`
- `figures/fig6_cdf_rslaq_style.png` e `.pdf`
- `figures/fig7_reliability_rslaq_style.png` e `.pdf`
- `figures/fig7_reliability_rslaq_style_including_insufficient.png` e `.pdf`

Figuras D/E de sensibilidade `P_STA` e prioridade invertida nao foram geradas porque os resultados existentes so cobrem `P_STA=0.5` e pesos padrao. Gera-las exigiria novos experimentos/alteracoes de configuracao DRL; isso fica para a Linha B.

## 9. Analise do cenario low_traffic

| scenario | slice | ues | packet_size_bytes | per_ue_rate_mbps | packet_interval_ms_estimated | trafego_oferecido_estimado_mbps | throughput_medido_mbps_max_observado | sla_minimo | sla_maximo_soft | nivel_medicao_throughput | status_fisico |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| low_traffic | eMBB | 5 | 1500 | 1 | 12 | 5 | 5.631 | 10 | 15 | FlowMonitor/IP UDP rxBytes delta; DRL KPM usa dRxBytes por periodo | aparentemente infactivel |
| low_traffic | URLLC | 5 | 50 | 0.2 | 2 | 1 | 1.56 | buffer <= 10000 bytes | sem soft max | FlowMonitor/IP UDP rxBytes delta; DRL KPM usa dRxBytes por periodo | factivel |
| low_traffic | MTC | 10 | 100 | 0.2 | 4 | 2 | 2.559 | no-policy no artigo | no-policy | FlowMonitor/IP UDP rxBytes delta; DRL KPM usa dRxBytes por periodo | inconclusivo por falta de metrica |

Leitura tecnica: no C++ lido somente para auditoria, `low_traffic` configura eMBB com 5 Mbps agregados para 5 UEs, pacote de 1500 bytes, aproximadamente 1 Mbps por UE e intervalo estimado de 12 ms por pacote. O SLA minimo eMBB do reward e 10 Mbps por slice. Como o throughput medido e goodput IP/UDP via FlowMonitor (`rxBytes` delta), nao ha evidencia de que retransmissoes ou bytes de controle estejam inflando a metrica. Assim, para eMBB em `low_traffic`, a incompatibilidade entre carga oferecida e SLA minimo e uma conclusao de auditoria de unidade/configuracao, nao uma suposicao previa.

## 10. Analise de reliability/outage

Outage foi calculado com as mesmas regras observaveis no reward:

- eMBB: throughput agregado do slice abaixo de `embb_min` quando ha demanda (`dTxBytes >= 1`).
- URLLC: `bufferBytes_max > 10000`.
- MTC: no-policy para outage, conforme implementacao.

Para baselines, a amostra e por timestamp de 10 ms. Para DRL, a fonte atual e: **snapshots finais rslaq-kpms.txt legados**. As tabelas `outage_by_seed.csv` e `reliability_by_seed.csv` explicitam a coluna `source`.

## 11. Ablations

Linha A paper-faithful: pesos originais, `P_STA=0.5`, SLAs originais implementados, soft terminal e DDQN com 198 acoes aplicando scheduler no ns-3.

Linha B ns-3-calibrada/ablation: suportada por argumentos (`--p_sta_static_fraction`, `--p_sta_weights`, `--reward_alpha`, `--reward_beta`, `--reward_gamma`). Recomendacao: rodar ao menos 5 seeds com mesmo orcamento DDQN/SAC, e entao testar SLAs recalibrados apenas se a incompatibilidade de carga oferecida for documentada por cenario.

## 12. Limitacoes

- Resultados legados ainda tem apenas seed 1 para RSLAQ/DDQN, SAC e baselines RSLAQ.
- Sem IC 95% para metricas principais, pois ha menos de 5 seeds.
- Sem tempo de treino/inferencia nos logs existentes.
- Logs novos por step corrigem a falta de outage por slice; resultados legados ainda nao.
- Scheduler escolhido pela acao DDQN foi corrigido no caminho IPC, mas resultados legados foram gerados antes dessa correcao.
- `low_traffic` tem carga eMBB oferecida abaixo do SLA minimo eMBB.

## 13. Parecer cientifico final

Classificacao: **reproducao parcial corrigida, estatisticamente inconclusiva ate nova campanha**.

A implementacao agora cobre os pontos estruturais centrais do RSLAQ no codigo, incluindo scheduler na acao DDQN. Ainda nao deve ser classificada como reproducao fiel completa com evidencia estatistica enquanto a campanha controlada multi-seed nao for executada e analisada.
