# Figuras comparativas - SLA e eficiencia de recursos

Campanhas analisadas:

- Baselines e SAC: `/home/elioth/Documentos/artigo_jussi/ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency/20260521_162404`
- DDQN/RSLAQ: `/home/elioth/Documentos/artigo_jussi/ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency/20260522_103413`

## Ranking agregado

| Metodo | SLA reliability medio | SLA satisfaction medio | Resource efficiency | Need-match | Over-allocation | Score composto |
|---|---:|---:|---:|---:|---:|---:|
| BCQI | 84.0% | 96.1% | NA | NA | NA | 0.462 |
| RR | 68.0% | 86.4% | NA | NA | NA | 0.374 |
| PF | 57.3% | 76.2% | NA | NA | NA | 0.315 |
| RSLAQ-DDQN | 35.1% | 41.7% | 0.106 | 0.672 | 0.278 | 0.312 |
| SAC-RSLAQ | 34.8% | 41.8% | 0.105 | 0.674 | 0.274 | 0.311 |
| SAC-ResourceEff | 34.8% | 41.8% | 0.105 | 0.675 | 0.273 | 0.312 |

## Leitura de pesquisador

- Maior cumprimento medio de SLA nesta campanha: **BCQI** (84.0% de reliability media).
- Melhor DRL em cumprimento de SLA: **RSLAQ-DDQN** (35.1% de reliability media).
- Melhor compromisso entre SLA e uso eficiente de recursos entre metodos com controle de PRB: **RSLAQ-DDQN** (score composto 0.312).
- Baselines RR/PF/BCQI nao fazem controle explicito de PRB por slice; por isso aparecem nos graficos de SLA, mas nao recebem score direto de eficiencia de alocacao por slice.
- As figuras `resource_efficiency`, `need_allocation_match`, `over_allocation` e `under_allocation` devem ser interpretadas como metricas de politica de alocacao, nao como throughput bruto.

## Por que as DRLs nao superaram os baselines nesta rodada

- A evidencia principal e o gap de SLA: os baselines tiveram reliability media agregada de **69.8%**, enquanto as DRLs ficaram em **34.9%**. Portanto, nesta configuracao, o controle aprendido de PRB reduziu a estabilidade do atendimento de SLA em vez de melhora-la.
- O problema de controle e muito dificil para o orcamento usado: cada ponto de decisao executa uma simulacao ns-3 ruidosa, com episodios curtos e terminacao por outage. Isso produz poucas transicoes uteis depois que a politica entra em estados ruins, especialmente em congestionamento e recursos insuficientes.
- O baseline BCQI explora diretamente a qualidade instantanea do canal no escalonador MAC. Ja o agente DRL atua em uma camada mais grossa, escolhendo percentuais de PRB por slice e, no DDQN, tambem um scheduler discreto. Essa acao agregada nao observa nem controla a granularidade fina por UE/RBG que favorece o BCQI.
- Ha desalinhamento entre recompensa e metrica final: a recompensa RSLAQ penaliza outage por limiares de eMBB, buffer URLLC e perdas MTC, enquanto a analise de SLA usa satisfacao por throughput/PDR por slice. O agente pode melhorar reward episodico sem necessariamente maximizar a metrica agregada de SLA usada no artigo.
- A decomposicao P_STA limita a liberdade da politica: metade da alocacao fica presa aos pesos estaticos. Isso protege isolamento, mas tambem reduz a capacidade do agente de reagir quando a demanda real favorece outro slice.
- A campanha tambem mostra sinal de acao pouco especializada: os scores de `need_allocation_match` ficam proximos entre as DRLs. Isso sugere que as politicas ainda nao aprenderam uma real adaptacao por cenario; elas tendem a operar perto de uma alocacao media, enquanto os baselines MAC continuam explorando diversidade de canal/UE.
- Como interpretacao para o artigo: o resultado nao invalida a contribuicao, mas mostra que a otimizacao DRL ainda esta limitada por representacao de estado, granularidade da acao, budget de treinamento e alinhamento da recompensa com SLA. A contribuicao de eficiencia deve ser apresentada como melhora marginal de alocacao entre DRLs, nao como superacao dos baselines MAC nesta rodada.

## Figuras geradas

- `fig_sla_satisfaction_by_scenario.png` / `fig_sla_satisfaction_by_scenario.pdf`
- `fig_sla_reliability_heatmap_by_slice.png` / `fig_sla_reliability_heatmap_by_slice.pdf`
- `fig_resource_efficiency_drl_methods.png` / `fig_resource_efficiency_drl_methods.pdf`
- `fig_sla_vs_resource_efficiency_tradeoff.png` / `fig_sla_vs_resource_efficiency_tradeoff.pdf`
- `fig_action_share_vs_need_share.png` / `fig_action_share_vs_need_share.pdf`
- `fig_reward_curves_by_scenario.png` / `fig_reward_curves_by_scenario.pdf`
