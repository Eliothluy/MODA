# Analise dos resultados com DDQN/RSLAQ

Resultados combinados:

- Baselines e SAC: `/home/elioth/Documentos/artigo_jussi/ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency/20260521_162404`
- DDQN/RSLAQ: `/home/elioth/Documentos/artigo_jussi/ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency/20260522_103413`
- Artefatos atualizados: `/home/elioth/Documentos/artigo_jussi/analysis_rslaq_validation/rslaq_sla_resource_efficiency_20260521_162404_with_ddqn_20260522_103413`

## Resultado agregado

| method | sla_reliability_mean_pct | sla_satisfaction_mean_pct | throughput_mean_mbps | pdr_mean_pct | resource_efficiency | need_allocation_match | over_allocation | resource_composite_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RR | 68 | 86.3831 | 19.1616 | 61.4193 | NA | NA | NA | 0.374 |
| PF | 57.3333 | 76.1566 | 12.2142 | 47.6249 | NA | NA | NA | 0.3153 |
| BCQI | 84 | 96.0861 | 33.6698 | 66.12 | NA | NA | NA | 0.462 |
| RSLAQ-DDQN | 35.0632 | 41.7006 | 3.6972 | 20.5414 | 0.1062 | 0.6723 | 0.2777 | 0.3122 |
| SAC-RSLAQ | 34.7807 | 41.7751 | 3.6925 | 20.9879 | 0.1046 | 0.6743 | 0.2741 | 0.3112 |
| SAC-ResourceEff | 34.7706 | 41.7832 | 3.6992 | 20.9876 | 0.1048 | 0.6754 | 0.2731 | 0.3116 |

O DDQN foi incorporado como `RSLAQ-DDQN`. Ele foi a melhor DRL em reliability media, com **35.06%**, mas continua muito abaixo dos baselines: `BCQI` atingiu **84.00%**, `RR` **68.00%** e `PF` **57.33%**. A conclusao empirica desta rodada e clara: a linha sem DRL, principalmente `BCQI`, cumpre as SLAs melhor do que os agentes treinados.

## Evidencia por slice

| method | MTC | URLLC | eMBB |
| --- | --- | --- | --- |
| RR | 92 | 92 | 20 |
| PF | 84 | 80 | 8 |
| BCQI | 84 | 88 | 80 |
| RSLAQ-DDQN | 0 | 100 | 5.19 |
| SAC-RSLAQ | 0 | 100 | 4.34 |
| SAC-ResourceEff | 0 | 100 | 4.31 |

A falha das DRLs nao e uniforme. Elas preservam `URLLC` em **100%** pela metrica de reliability usada, mas praticamente nao cumprem `MTC` (**0%**) e quase nao cumprem `eMBB` (**4.31% a 5.19%**). O `BCQI`, por outro lado, mantem desempenho alto e mais equilibrado: **80%** em `eMBB`, **88%** em `URLLC` e **84%** em `MTC`.

Isso indica que os agentes aprenderam uma politica conservadora para URLLC, mas nao aprenderam a redistribuir recursos para eMBB/MTC quando a demanda exige. Portanto, o problema nao e apenas "DRL ruim"; e um desalinhamento entre representacao/acao/recompensa e o objetivo multi-slice medido no final.

## Evidencia por cenario

| scenario | BCQI | PF | RR | RSLAQ-DDQN | SAC-RSLAQ | SAC-ResourceEff |
| --- | --- | --- | --- | --- | --- | --- |
| low_traffic | 87.53 | 76.82 | 89.71 | 73.94 | 74.47 | 74.46 |
| normal | 92.9 | 69.91 | 88.81 | 67.16 | 66.95 | 66.95 |
| congestion | 100 | 80.18 | 81.93 | 0.14 | 0.14 | 0.14 |
| stressed | 100 | 75.7 | 86.74 | 66.58 | 66.63 | 66.68 |
| insufficient_resources | 100 | 78.17 | 84.73 | 0.68 | 0.68 | 0.68 |

Os cenarios que mais expoem o problema sao `congestion` e `insufficient_resources`. Neles, as DRLs ficam praticamente zeradas em satisfacao media de SLA: cerca de **0.14%** em `congestion` e **0.68%** em `insufficient_resources`. O `BCQI` aparece com **100%** nos mesmos cenarios pela metrica agregada dos CSVs de baseline. Mesmo que essa comparacao tenha diferencas metodologicas entre baseline ns-3 e step metrics dos agentes, a distancia e grande o suficiente para indicar que o controle DRL atual nao esta estabilizando o sistema.

## Uso de recurso por slice

| method | resource_efficiency_calc | need_allocation_match_calc | over_allocation_calc | under_allocation_calc | served_score |
| --- | --- | --- | --- | --- | --- |
| RSLAQ-DDQN | 0.1062 | 0.6723 | 0.2777 | 0.2908 | 0.1714 |
| SAC-RSLAQ | 0.1046 | 0.6743 | 0.2741 | 0.2894 | 0.1736 |
| SAC-ResourceEff | 0.1048 | 0.6754 | 0.2731 | 0.2883 | 0.1734 |

| method | alloc_embb | alloc_urllc | alloc_mtc | need_embb | need_urllc | need_mtc |
| --- | --- | --- | --- | --- | --- | --- |
| RSLAQ-DDQN | 34.1 | 35.74 | 30.16 | 63.94 | 14.52 | 21.53 |
| SAC-RSLAQ | 32.99 | 36.54 | 30.47 | 64.26 | 14.44 | 21.3 |
| SAC-ResourceEff | 33.07 | 36.47 | 30.46 | 64.22 | 14.46 | 21.32 |

A causa operacional mais forte aparece na comparacao entre alocacao media e necessidade estimada. As DRLs alocam aproximadamente **33% eMBB / 36% URLLC / 30% MTC**, mas a necessidade estimada pela demanda fica perto de **64% eMBB / 14% URLLC / 21% MTC**. Ou seja, os agentes subalocam eMBB em cerca de **31 pontos percentuais** e superalocam URLLC em cerca de **22 pontos percentuais**.

Essa politica explica simultaneamente:

- baixa reliability de `eMBB`, porque o slice que mais demanda throughput recebe metade do recurso que a demanda indicaria;
- reliability perfeita de `URLLC`, porque o slice recebe muito mais recurso do que sua necessidade media estimada;
- reliability nula de `MTC`, possivelmente por perdas recorrentes e por a recompensa/acao nao corrigirem perdas pequenas mas frequentes.

## Por que o baseline supera a otimizacao por ML

1. **O baseline nao e ingenuo.** `BCQI`, `PF` e `RR` sao escalonadores MAC consolidados. Em especial, `BCQI` usa informacao instantanea de qualidade de canal e explora diversidade multiusuario em granularidade fina de RBG/UE. O agente DRL controla percentuais por slice, uma acao mais grosseira.

2. **Granularidade da acao.** A politica escolhe shares de PRB por slice, mas quem decide quais UEs recebem recurso ainda e o scheduler ns-3. Se o share escolhido pelo agente estiver errado, o scheduler interno nao consegue recuperar completamente o SLA entre slices.

3. **P_STA prende parte da decisao.** Com `P_STA_STATIC_FRACTION=0.5` e pesos `0.3333,0.4000,0.2667`, metade da alocacao permanece ancorada em uma distribuicao estatica. Isso ajuda isolamento, mas reduz adaptacao quando o eMBB passa a dominar a demanda.

4. **Recompensa e metrica final nao estao perfeitamente alinhadas.** A recompensa RSLAQ penaliza throughput eMBB, buffer URLLC e perdas MTC. Ja a avaliacao final agrega satisfacao por SLA, reliability, PDR e throughput. O agente pode maximizar uma recompensa episodica parcial sem maximizar a metrica usada na comparacao final.

5. **Orcamento de treinamento pequeno para ns-3 online.** A campanha usa episodios curtos, com amostras caras e ruidosas. Para DDQN, a exploracao discreta em uma tabela grande de acoes dificulta convergir; para SAC, a politica continua perto de uma alocacao media. Os scores de `need_allocation_match` muito proximos entre DRLs confirmam que ainda nao houve especializacao forte por cenario.

6. **Terminacao por outage reduz aprendizado em estados ruins.** Quando o episodio termina cedo, o agente recebe sinal de falha, mas coleta poucas transicoes que mostrem como sair da condicao ruim. Isso piora justamente nos cenarios de congestionamento e recursos insuficientes.

## Interpretacao para o artigo

Nesta rodada, a afirmacao defensavel e:

> Os baselines MAC, principalmente BCQI, cumprem melhor as SLAs do que as politicas DRL treinadas. Entre as DRLs, o DDQN/RSLAQ foi ligeiramente melhor em reliability agregada, enquanto a recompensa de eficiencia melhora marginalmente o alinhamento alocacao-demanda em relacao ao SAC-RSLAQ. A contribuicao deve ser posicionada como diagnostico e melhoria de eficiencia de alocacao, ainda nao como superacao dos escalonadores MAC baselines.

Para transformar a contribuicao em resultado competitivo, os proximos experimentos devem priorizar: alinhar a recompensa diretamente com a metrica de SLA final, reduzir ou tornar adaptativo o peso estatico do P_STA, aumentar o budget de treinamento, treinar por curriculo de cenarios e expor ao agente features de demanda/canal que expliquem melhor por que o eMBB esta sendo subalocado.
