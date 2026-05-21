# Relatorio das Alteracoes RSLAQ DRL

## Objetivo

Este relatorio descreve as mudancas implementadas para validar o cenario RSLAQ ajustado com a recompensa original do artigo e para adicionar uma nova recompensa orientada a eficiencia de recursos por slice.

A implementacao preserva a recompensa RSLAQ original como baseline cientifico (`reward_mode="paper"`) e adiciona uma contribuicao selecionavel (`reward_mode="resource_efficient"`) para treinar o agente SAC a cumprir SLA usando os recursos de slice de forma mais eficiente.

## Arquivos alterados

- `ns-o-ran-gym/src/environments/rslaq_reward.py`
  - Mantem a recompensa RSLAQ do artigo como modo padrao `paper`.
  - Adiciona o modo `resource_efficient`.
  - Adiciona termos de eficiencia: casamento demanda-alocacao, desperdicio, subalocacao e suavidade da acao.

- `ns-o-ran-gym/src/environments/rslaq_env.py`
  - Propaga `reward_mode` via `sla_config`.
  - Registra `previous_prb_pct` para penalizar oscilacoes bruscas de acao.
  - Adiciona colunas no `step_metrics.csv` para analisar eficiencia de recursos.

- `ns-o-ran-gym/examples/rslaq_train_sac.py`
  - Adiciona argumentos CLI para selecionar a recompensa e configurar os pesos da nova funcao.
  - Registra `reward_mode` no log de treinamento.
  - Inclui metadados da recompensa no `sac_summary.json`.

- `ns-o-ran-gym/examples/run_controlled_rslaq_validation.sh`
  - Reorganiza a campanha controlada em tres linhas experimentais:
    - `baseline_ns3`: simulacao ns-3 pura, sem DRL.
    - `sac_paper`: SAC com a recompensa RSLAQ original.
    - `sac_resource_efficient`: SAC com a nova recompensa proposta.
  - Mantem DDQN opcional com `RUN_DDQN=1`.

- `ns-o-ran-gym/examples/compare_rslaq_campaigns.py`
  - Reconhece diretorios `sac_paper_*` e `sac_resource_efficient_*`.
  - Agrega metricas de eficiencia alem das metricas de SLA.

- `ns-o-ran-gym/tests/test_rslaq_reward.py`
  - Adiciona testes para garantir que o modo `paper` preserva o comportamento original.
  - Adiciona testes para a nova recompensa eficiente.

## Recompensa RSLAQ original

A recompensa original permanece como a referencia do artigo RSLAQ. Para cada passo de controle, o ambiente calcula os termos de otimizacao por slice.

Para o slice eMBB:

$$
h_1 = \min\left(\frac{\bar{T}_{eMBB}}{T_{max}}, 1\right)
$$

onde:

$$
\bar{T}_{eMBB} = \frac{T_{eMBB}}{|\Lambda_{eMBB}|}
$$

Para o slice URLLC:

$$
h_2 = \exp\left(-\frac{B^{max}_{URLLC}}{B_{norm}}\right)
$$

Para o slice MTC:

$$
h_3 = \min\left(\frac{\bar{T}_{MTC}}{T_{max}}, 1\right)
$$

onde:

$$
\bar{T}_{MTC} = \frac{T_{MTC}}{|\Lambda_{MTC}|}
$$

A recompensa de otimizacao do RSLAQ e:

$$
r_{opt} = \alpha h_1 + \beta h_2 + \gamma h_3 + \mathbb{1}_{sched}\frac{1}{c(s)}
$$

No modo SAC continuo atual, o termo de scheduler normalmente nao e usado, pois `scheduler_id = -1`. Assim, na pratica:

$$
r_{opt} = \alpha h_1 + \beta h_2 + \gamma h_3
$$

com pesos padrao:

$$
\alpha = 0.3333, \quad \beta = 0.4000, \quad \gamma = 0.2667
$$

As condicoes terminais seguem a logica RSLAQ:

$$
r_{RSLAQ} =
\begin{cases}
-\sum_{j \in \mathcal{O}} \omega_j, & \text{se houver outage de SLA} \\
0, & \text{se houver violacao soft de SLA} \\
r_{opt}, & \text{caso contrario}
\end{cases}
$$

onde $\mathcal{O}$ e o conjunto de slices em outage e $\omega_j$ representa o peso de prioridade do slice.

## Nova recompensa proposta: eficiencia de recursos por slice

A nova contribuicao nao substitui a logica de SLA do RSLAQ. Ela atua como um termo adicional de shaping somente quando nao ha terminacao por violacao de SLA. Isso evita que o agente aprenda a economizar PRBs as custas do SLA.

A recompensa final proposta e:

$$
r_{eff} =
\begin{cases}
r_{RSLAQ}, & \text{se houver terminacao por outage ou soft SLA} \\
r_{RSLAQ} + \Delta r_{eff}, & \text{caso contrario}
\end{cases}
$$

O termo adicional e:

$$
\Delta r_{eff} =
\lambda_E E
+ \lambda_M M
- \lambda_O O
- \lambda_U U
- \lambda_S S
$$

com pesos padrao:

$$
\lambda_E = 0.20, \quad
\lambda_M = 0.15, \quad
\lambda_O = 0.25, \quad
\lambda_U = 0.10, \quad
\lambda_S = 0.05
$$

### Vetor de alocacao

A alocacao enviada pelo agente para cada slice e normalizada como:

$$
a_j = \frac{p_j}{\sum_k p_k}
$$

onde $p_j$ e o percentual de PRB alocado ao slice $j$.

### Necessidade dinamica do slice

A necessidade bruta de cada slice e calculada a partir de trafego transmitido, buffer e perdas:

$$
n_j = TX_j + B_j + C_L L_j
$$

onde:

- $TX_j$ e o volume transmitido do slice.
- $B_j$ e o maior buffer observado no slice.
- $L_j$ e o numero de pacotes perdidos.
- $C_L$ e o equivalente em bytes por pacote perdido, com padrao $1500$ bytes.

Foram adicionados ajustes por tipo de slice:

Para eMBB, se a vazao estiver abaixo da meta minima:

$$
n_0 \leftarrow n_0\left(1 + \min\left(\frac{K_{eMBB} - T_0}{K_{eMBB}}, 1\right)\right)
$$

Para URLLC, a pressao de buffer aumenta a necessidade:

$$
n_1 \leftarrow n_1 + \min\left(\frac{B_1}{K_{URLLC}}, 2\right)K_{URLLC}
$$

Para MTC, se a vazao estiver abaixo da meta:

$$
n_2 \leftarrow n_2\left(1 + 0.5\min\left(\frac{K_{MTC} - T_2}{K_{MTC}}, 1\right)\right)
$$

A participacao dinamica da demanda e:

$$
d_j = \frac{n_j}{\sum_k n_k}
$$

Se nao houver demanda observavel, o codigo usa os pesos estaticos do RSLAQ como fallback.

### Alvo de alocacao eficiente

O alvo de alocacao mistura os pesos estaticos do RSLAQ com a demanda dinamica medida:

$$
q_j = (1 - \rho)\omega_j + \rho d_j
$$

onde $\rho$ controla quanto o alvo segue a demanda dinamica. O valor padrao e:

$$
\rho = 0.75
$$

### Casamento demanda-alocacao

A qualidade do casamento entre alocacao real e necessidade estimada e:

$$
M = \max\left(0, 1 - \frac{1}{2}\sum_j |a_j - q_j|\right)
$$

Quanto mais proximo $a_j$ estiver de $q_j$, maior sera $M$.

### Penalidade por desperdicio

A superalocacao e:

$$
O = \sum_j \max(a_j - q_j - \epsilon, 0)
$$

A subalocacao e:

$$
U = \sum_j \max(q_j - a_j - \epsilon, 0)
$$

com tolerancia padrao:

$$
\epsilon = 0.03
$$

### Eficiencia de entrega

A fracao servida por slice e:

$$
s_j = \min\left(\frac{RX_j}{TX_j}, 1\right)
$$

A eficiencia de recursos usada na recompensa e:

$$
E = M \sum_j q_j s_j
$$

Assim, a recompensa so cresce quando a alocacao esta alinhada a necessidade e o trafego e efetivamente entregue.

### Suavidade da acao

Para evitar oscilacoes bruscas de PRB entre passos consecutivos:

$$
S = \frac{1}{2}\sum_j |a_j(t) - a_j(t-1)|
$$

Esse termo penaliza mudancas abruptas na politica de alocacao.

## Como executar

Campanha completa:

```bash
cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
bash examples/run_controlled_rslaq_validation.sh
```

Campanha curta para validacao:

```bash
cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
SCENARIOS="normal" SEEDS="1" INTERACTION_STEPS=100 EPISODE_STEPS=20 \
bash examples/run_controlled_rslaq_validation.sh
```

Executar somente SAC com a nova recompensa:

```bash
cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
RUN_BASELINES=0 RUN_PAPER_SAC=0 RUN_RESOURCE_EFFICIENT_SAC=1 \
SCENARIOS="normal" SEEDS="1" \
bash examples/run_controlled_rslaq_validation.sh
```

## Parametros principais da nova recompensa

- `RESOURCE_EFFICIENCY_WEIGHT`: peso positivo para eficiencia de entrega alinhada a demanda.
- `NEED_MATCH_WEIGHT`: peso positivo para casar PRB alocado com necessidade dinamica.
- `WASTE_PENALTY_WEIGHT`: penalidade por superalocacao.
- `UNDER_ALLOCATION_PENALTY_WEIGHT`: penalidade por subalocacao.
- `ACTION_SMOOTHNESS_WEIGHT`: penalidade por oscilacao da acao.
- `RESOURCE_DYNAMIC_NEED_WEIGHT`: mistura entre pesos RSLAQ estaticos e demanda dinamica.
- `RESOURCE_WASTE_DEADBAND`: tolerancia antes de penalizar sobre/subalocacao.

## Validacao realizada

Foram executadas as seguintes validacoes:

```bash
python3 -m py_compile \
  ns-o-ran-gym/src/environments/rslaq_reward.py \
  ns-o-ran-gym/src/environments/rslaq_env.py \
  ns-o-ran-gym/examples/rslaq_train_sac.py \
  ns-o-ran-gym/examples/compare_rslaq_campaigns.py
```

```bash
bash -n ns-o-ran-gym/examples/run_controlled_rslaq_validation.sh
```

```bash
python3 ns-o-ran-gym/tests/test_rslaq_reward.py
```

Tambem foi executada uma campanha de fumaca com:

- 1 cenario: `low_traffic`
- 1 seed: `1`
- baseline ns-3: `pure_pf`
- SAC com recompensa `paper`
- SAC com recompensa `resource_efficient`

Saida gerada em:

```text
ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency/smoke_resource_reward
```

## Interpretacao esperada

A linha `sac_paper` avalia se a funcao de recompensa RSLAQ do artigo funciona no cenario ajustado e se o agente consegue cumprir SLA.

A linha `sac_resource_efficient` avalia a contribuicao proposta: cumprir SLA enquanto reduz desperdicio de PRBs e melhora o alinhamento entre demanda real e alocacao por slice.

A comparacao deve priorizar:

- confiabilidade de SLA;
- taxa de outage;
- taxa de soft violation;
- throughput por slice;
- buffer URLLC;
- PRB medio por slice;
- `resource_efficiency`;
- `need_allocation_match`;
- `over_allocation`;
- `under_allocation`.
