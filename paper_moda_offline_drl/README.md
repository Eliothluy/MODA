# MODA — Metaheuristic-Offline Distilled Allocation for RAN Slicing

Artefatos prontos para o artigo (figuras IEEE + tabelas LaTeX/booktabs) da linha
de **DRL offline** que estende a campanha de metaheurísticas. Esta linha é uma
**extensão** do artigo principal (cujo foco é a comparação de metaheurísticas —
ver `AGENTS.md`); não é o resultado central.

## 1. Nome da proposta e da DRL

**MODA — *Metaheuristic-Offline Distilled Allocation***: um arcabouço que
**destila** a experiência offline gerada pela busca metaheurística (avaliações
ns-3 reais de GA/PSO/SA/híbrido sobre o simplex de pesos de PRB por slice
`[eMBB, URLLC, MTC]`) em **políticas neurais rápidas** de alocação de slice,
implantáveis como **xApp O-RAN** (inferência em <1 ms, sem re-executar o ns-3).

Três variantes (mesma entrada = estado da rede; mesma saída = vetor de pesos no
simplex), nomeadas pela **receita de treino** — nomenclatura honesta, pois os
dados registrados **não têm próximo-estado**, logo nenhuma usa TD-learning nem
rollouts de policy-gradient:

| Nome no paper | DRL base | Receita de treino offline |
|---|---|---|
| **MODA-Q** *(principal)* | **DDQN** | Regressão de valor Q sobre o simplex discretizado (66 bins) |
| **MODA-BC** | SAC | Clonagem comportamental (behavioral cloning) do top-20% de candidatos |
| **MODA-RWR** | PPO | Regressão ponderada por recompensa (reward-weighted regression, τ=0.1) |

> **Recomendação de redação:** apresente **MODA** como o arcabouço e **MODA-Q
> (DDQN offline)** como a instância principal; use MODA-BC e MODA-RWR como
> *ablations* da receita de treino. Isso evita o rótulo enganoso "DDQN/SAC/PPO"
> (que sugeriria RL online com TD/PG), coerente com o que o próprio código
> documenta em `nsoran/offline_models.py`.

**Bases de comparação** (executadas no mesmo ambiente ns-3, portanto
comparáveis): `Best meta.` (melhor candidato metaheurístico re-executado),
`RSLAQ fixed [0.33,0.40,0.27]` e `Equal [1/3,1/3,1/3]`.

## 2. Metodologia de avaliação (o que torna os números defensáveis)

- **Malha fechada real:** cada vetor de pesos previsto é executado como um run
  ns-3 (`--baselineMode=slice_custom`, `--intraAlgo=PF`, `simTime=5`, mesmos
  parâmetros da Fase 2 da campanha) e pontuado com a função-objetivo da campanha
  (`nsoran.scoring.score_summary_rows`). **Não** se usa o proxy de
  vizinho-mais-próximo (circular e descontínuo) do `eval_offline_rl.py` original.
- **Mesmo ambiente para todos:** descobrimos que pesos idênticos rendem scores
  diferentes entre máquinas/toolchains (até ±47 pts). Por isso **todas** as
  linhas — inclusive `Best meta.` — foram re-executadas na máquina atual.
- **N = 3 seeds (1, 2, 3)** por projeto (`AGENTS.md`): reportamos
  **média ± desvio**, sem alegações de significância estatística.

## 3. Figuras (`figures/`, PNG 300 dpi + PDF vetorial)

| Arquivo | Conteúdo | Mensagem |
|---|---|---|
| `fig1_composite_score` | Score composto (média±desvio) por método × cenário | MODA ≈ baselines onde há folga; MODA-BC/Q lideram em congestion |
| `fig2_goodput_per_rbg` | Goodput por RBG alocado (B) — eficiência espectral | MODA-Q rende mais payload por PRB sob escassez |
| `fig3_worst_slice_sla` | Satisfação de SLA da **pior** slice (%) | MODA evita violar SLA da slice mais fraca |
| `fig4_congestion_rbg_share` | Partição de RBG por slice em congestion (empilhado) | **Mecanismo:** MODA preserva o MTC; o ótimo metaheurístico o mata de fome |
| `fig5_robustness_frontier` | Score médio × desvio entre seeds | MODA troca pico por robustez |

## 4. Tabelas (`tables/`, LaTeX booktabs — requer `\usepackage{booktabs}`)

| Arquivo | Conteúdo |
|---|---|
| `table1_composite_scores.tex` | Score composto (média±desvio), melhor por cenário em negrito |
| `table2_radio_efficiency.tex` | Eficiência de rádio (goodput/RBG e SLA de pior-caso) em congestion e stressed |
| `table3_congestion_per_slice.tex` | Alocação e QoS por slice em congestion (evidencia a inanição do MTC) |

## 5. Dados de apoio (`data/`)

`scores_per_seed.csv`, `scores_aggregate.csv`, `radio_per_slice.csv`,
`radio_cell.csv` — tabelas limpas (rótulos MODA-*) que originam as figuras.

## 6. Principais achados (para a discussão)

1. **A eficiência de recursos só se decide sob escassez.** Em `low`/`normal` há
   PRB sobrando: qualquer partição (eMBB de 55% a 81%) rende vazão e PDR quase
   iguais. MODA ≈ baselines fixos nesses casos.
2. **Sob `congestion`, MODA-Q e MODA-BC dominam:** ~17 Mb/s a mais de vazão
   servida, maior goodput/RBG (45.9 vs 33–40 B) e melhor SLA de pior-caso que os
   baselines fixos **e** que o ótimo metaheurístico re-executado.
3. **Robustez > otimalidade pontual.** O ótimo metaheurístico `[0.816, 0.180,
   0.004]` maximiza o score médio da campanha mas **estrangula o MTC**
   (delay > 1 s, SLA 73.7%) e colapsa em uma das 3 seeds (score 61.8 ± 32.9 em
   congestion). MODA aprendeu uma alocação mais balanceada e estável.
4. **Limitações honestas (declarar no paper):** (i) o estado tem apenas
   **4 configurações distintas** (uma por cenário) — as políticas são, hoje,
   seletores estáticos de peso por cenário, não controladores dinâmicos; um
   xApp verdadeiramente dinâmico exige um dataset com transições por timestep
   (linha de trabalho futura, minerável de `heuristics_ns3/`); (ii) N=3;
   (iii) 1 run de MODA-RWR/congestion falhou no ns-3 (n=2 nessa célula).

## 7. Reprodução

```bash
cd ns-o-ran-gym
# 1) avaliação em malha fechada (gera models/evaluation_closedloop*.csv)
python3 examples/eval_offline_rl_closedloop.py --jobs 6
# 2) métricas de eficiência de rádio (gera models/closedloop_radio_efficiency_*.csv)
python3 examples/analyze_closedloop_radio_efficiency.py
# 3) figuras + tabelas deste diretório
python3 examples/generate_moda_paper_artifacts.py
```

Scripts-fonte: `examples/eval_offline_rl_closedloop.py`,
`examples/analyze_closedloop_radio_efficiency.py`,
`examples/generate_moda_paper_artifacts.py`.
