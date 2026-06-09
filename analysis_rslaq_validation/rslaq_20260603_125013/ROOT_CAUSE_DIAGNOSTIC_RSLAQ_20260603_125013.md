# Diagnostico de causa-raiz do protocolo RSLAQ

## Conclusao curta

A campanha atual nao prova que as DRLs sao intrinsecamente piores que RR/PF/BCQI. Ela prova que, com o protocolo atual, os KPIs logados durante treino/exploracao ficam abaixo dos baselines. A causa mais provavel e experimental: avaliacao misturada com treino, acoes exploratorias/estocasticas, cobertura incompleta em alguns casos, terminacoes precoces no Predictive-SAC e score original com dupla contagem efetiva de perda via PDR e PLR.

## Evidencias principais

- O runner usa `SEED_CYCLE=999999`; assim, a seed do ns-3 fica fixa dentro de uma execucao longa, salvo campanhas muito maiores que esse ciclo.
- DDQN registra KPIs enquanto ainda usa epsilon-greedy; o padrao tem `epsilon_min=0.05`, portanto a avaliacao tardia ainda inclui exploracao.
- SAC e Predictive-SAC registram KPIs usando `actor.sample`, portanto as acoes logadas sao amostras estocasticas, nao a media deterministica da politica.
- A comparacao atual usa o trecho final do treinamento como proxy de avaliacao; isso nao substitui avaliacao pos-treino com politica congelada.
- `Predictive-SAC` apresenta muitos episodios curtos/terminados; nesses casos a comparacao mede falhas de horizonte curto, nao desempenho estacionario.
- O score original inclui `pdr_score` e `plr_score`. Para DRL, `pdr_pct = 100 - plr_pct`; para baseline, `plr_pct` aparece 0 mesmo quando `pdr_pct < 100`. Isso favorece baseline por construcao e duplica a penalizacao de perda na DRL.

## Cobertura e runs suspeitos

| method | scenario | labelled_seeds | step_files | steps_logged_mean | terminated_steps_sum | missing_labelled_seeds | has_short_episodes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Predictive-SAC | congestion | 4 | 660 | 13.5273 | 600 | 1 | True |
| Predictive-SAC | low_traffic | 5 | 1000 | 5.5950 | 1000 | 0 | True |
| Predictive-SAC | normal | 5 | 1000 | 5.0120 | 1000 | 0 | True |
| SAC-ResourceEff | congestion | 4 | 800 | 100.0000 | 0 | 1 | False |

## Sensibilidade do score

`score_original` reproduz o score do relatorio anterior. `score_no_plr` remove a dupla contagem direta de `PLR`, mantendo throughput/PDR para eMBB/MTC e PDR/buffer para URLLC.

| scenario | score_variant | best_drl_method | best_drl_score | best_baseline_method | best_baseline_score | gap_pct |
| --- | --- | --- | --- | --- | --- | --- |
| congestion | score_no_plr | SAC-ResourceEff | 0.5883 | RR | 0.7194 | -18.2222 |
| congestion | score_original | SAC-ResourceEff | 0.5202 | BCQI | 0.8589 | -39.4367 |
| congestion | score_pdr_only | SAC-ResourceEff | 0.3839 | BCQI | 0.5768 | -33.4380 |
| congestion | score_thr_pdr_all_slices | SAC-ResourceEff | 0.6920 | BCQI | 0.7884 | -12.2320 |
| low_traffic | score_no_plr | SAC-Paper | 0.7039 | PF | 0.7632 | -7.7622 |
| low_traffic | score_original | SAC-Paper | 0.6921 | PF | 0.8496 | -18.5387 |
| low_traffic | score_pdr_only | SAC-Paper | 0.6684 | PF | 0.8096 | -17.4471 |
| low_traffic | score_thr_pdr_all_slices | SAC-Paper | 0.7013 | PF | 0.7744 | -9.4331 |
| normal | score_no_plr | SAC-Paper | 0.6757 | RR | 0.6835 | -1.1484 |
| normal | score_original | SAC-Paper | 0.6464 | RR | 0.8254 | -21.6852 |
| normal | score_pdr_only | SAC-Paper | 0.5878 | RR | 0.6985 | -15.8379 |
| normal | score_thr_pdr_all_slices | SAC-Paper | 0.6820 | RR | 0.7380 | -7.5927 |

## Ranking medio por variante

| method | source | runs | score_original | score_no_plr | score_pdr_only | score_thr_pdr_all_slices |
| --- | --- | --- | --- | --- | --- | --- |
| RR | baseline | 25 | 0.8532 | 0.7330 | 0.6587 | 0.7798 |
| PF | baseline | 25 | 0.8468 | 0.7212 | 0.6421 | 0.7702 |
| BCQI | baseline | 25 | 0.8510 | 0.7204 | 0.6550 | 0.7765 |
| SAC-ResourceEff | DRL-late-training | 14 | 0.6253 | 0.6601 | 0.5556 | 0.6903 |
| SAC-Paper | DRL-late-training | 15 | 0.6169 | 0.6532 | 0.5442 | 0.6904 |
| DDQN-Paper | DRL-late-training | 15 | 0.6091 | 0.6474 | 0.5326 | 0.6846 |
| DDQN-ResourceEff | DRL-late-training | 15 | 0.5967 | 0.6382 | 0.5135 | 0.6751 |
| Predictive-SAC | DRL-late-training | 14 | 0.4266 | 0.4750 | 0.3296 | 0.4343 |

## Protocolo recomendado antes de concluir cientificamente

1. Treinar a politica com uma seed de treino registrada, mas avaliar em uma fase separada com politica congelada.
2. DDQN: avaliacao com `epsilon=0` e sem replay/update durante os episodios de avaliacao.
3. SAC/Predictive-SAC: avaliacao com acao deterministica baseada em `tanh(mean)`, nao `actor.sample`.
4. Separar `training_seed`, `ns3_seed` e `replicate_id`; repetir `seed=1` tres vezes sem mudar RNG nao e uma replica independente.
5. Executar pelo menos `5 ns3_seeds x 3 training_replicates` por metodo/cenario, ou `15` seeds independentes por metodo/cenario, com todos os metodos no mesmo conjunto de cargas.
6. Comparar primeiro por metricas fisicas comuns: throughput por slice, PDR, buffer URLLC, delay/jitter quando disponivel, SLA/outage rate e eficiencia de recurso. Reward deve ficar separado por modo (`paper` vs `resource_efficient`).
7. Corrigir o score composto: usar PDR ou PLR, nao ambos, salvo se os logs de baseline e DRL tiverem semantica identica para perda.
