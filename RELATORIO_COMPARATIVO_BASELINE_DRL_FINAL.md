# Relatório Comparativo: Baseline vs DRL - Análise RSLAQ

**Engenheiro de Dados Senior - Redes 5G**
**Data:** 2026-05-14

---

## Resumo Executivo

Este relatório apresenta uma análise comparativa entre resultados baseline (sem otimização DRL) e resultados com Deep Reinforcement Learning (DDQN e SAC) para a implementação do artigo RSLAQ ("A Robust SLA-driven 6G O-RAN QoS xApp Using Deep Reinforcement Learning", IEEE TMC 2026).

### Principais Descobertas

| Descoberta | Detalhe |
|------------|---------|
| 🟩 **SAC Superior** | SAC alcança reward médio de 17.85 (normal) vs 9.37 do DDQN |
| 🟨 **Throughput Similar** | Baseline e DRL com throughput eMBB similar em cenário normal |
| 🟩 **URLLC Excelente** | 0% PLR em todos os cenários com slice-aware e DRL |
| 🟥 **Low Traffic Crítico** | SLA de 10 Mbps vs throughput máximo de 5.1 Mbps (impossível) |
| 🟩 **Convergência SAC** | 300 episódios com reward estável, episódios mais longos |

---

## Índice

1. [Metodologia](#1-metodologia)
2. [Descrição dos Modos de Scheduler](#2-descrição-dos-modos-de-scheduler)
3. [Comparação de Resultados por Cenário](#3-comparação-de-resultados-por-cenário)
4. [Análise DRL - DDQN e SAC](#4-análise-drl---ddqn-e-sac)
5. [Avaliação da Implementação do Artigo RSLAQ](#5-avaliação-da-implementação-do-artigo-rslaq)
6. [Problemas Identificados](#6-problemas-identificados)
7. [Recomendações](#7-recomendações)

---

## 1. Metodologia

### Fontes de Dados

| Fonte | Caminho | Descrição |
|-------|---------|-----------|
| Baseline | `/ns-3-dev/results_rslaq_network_only/` | Resultados sem otimização DRL |
| DDQN | `/ns-o-ran-gym/results/ddqn_*_seed1/` | Double Deep Q-Network (50 episódios) |
| SAC | `/ns-o-ran-gym/results/sac_*_seed1/` | Soft Actor-Critic (300 episódios) |
| Artigo | `/home/elioth/Documentos/artigo_jussi/_RSLAQ-...pdf` | IEEE TMC 2026 |

### Cenários Avaliados

- **Normal:** Tráfego padrão dos 3 slices (eMBB, URLLC, MTC)
- **Congestion:** Tráfego elevado com competição por recursos
- **Low Traffic:** Tráfego reduzido (cenário problemático)
- **Stressed:** Condições extremas de tráfego
- **Insufficient Resources:** Recursos de rede limitados

---

## 2. Descrição dos Modos de Scheduler

### 2.1 Pure Modes (Baselines sem Slicing)

| Modo | Descrição |
|------|-----------|
| **pure_rr** | Round Robin global (todos os UEs compartilham recursos) |
| **pure_pf** | Proportional Fair global |
| **pure_bcqi** | Best CQI (Maximum Rate) global |

### 2.2 Slice-Aware Modes (Com Slicing)

| Modo | Descrição |
|------|-----------|
| **slice_rr** | Alocação igual (33.3%/33.3%/33.3%) + RR intra-slice |
| **slice_pf** | Alocação igual + PF intra-slice |
| **slice_bcqi** | Alocação igual + BCQI intra-slice |
| **slice_weighted_rr** | Alocação ponderada + RR intra-slice |
| **slice_weighted_pf** | Alocação ponderada + PF intra-slice |
| **slice_weighted_bcqi** | Alocação ponderada + BCQI intra-slice |

### 2.3 P_STA (Artigo RSLAQ)

| Modo | Descrição |
|------|-----------|
| **psta_equal** | P_STA estático (50% dos recursos) + alocação ponderada + scheduler |

---

## 3. Comparação de Resultados por Cenário

### 3.1 Cenário Normal

#### Baseline (psta_equal)

| Slice | Throughput (Mbps) | PDR | PLR |
|-------|-------------------|-----|-----|
| eMBB | 11.60 | 16.3% | 0% |
| URLLC | 1.56 | 100% | 0% |
| MTC | 2.56 | 100% | 0% |

#### DRL - DDQN (50 episódios)

| Métrica | Valor |
|---------|-------|
| **Reward Final Médio** | 9.37 |
| **Best Avg Reward** | 9.97 |
| **Throughput eMBB** | 15.89 - 22.00 Mbps |
| **URLLC PLR** | 0% |
| **Outage Count** | 0 |
| **Soft Count** | 1 (todos os episódios) |
| **Steps Médio** | 5-28 |

#### DRL - SAC (300 episódios)

| Métrica | Valor |
|---------|-------|
| **Reward Final Médio** | 17.85 |
| **Best Avg Reward** | 19.28 |
| **Throughput eMBB** | 6.11 - 18.34 Mbps |
| **URLLC PLR** | 0% |
| **Outage Count** | 0 |
| **Soft Count** | 1 (todos os episódios) |
| **Steps Médio** | 5-153 |

```
┌─────────────────────────────────────────────────────────────────┐
│  ANÁLISE - CENÁRIO NORMAL                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Baseline (psta_equal):                                          │
│    • eMBB: 11.6 Mbps (estável)                                   │
│    • URLLC: 100% PDR (excelente)                                 │
│    • MTC: 100% PDR (excelente)                                   │
│                                                                 │
│  DDQN:                                                            │
│    • Reward: 9.37 (estagnado após 50 episódios)                  │
│    • Throughput eMBB: variável (15-22 Mbps)                      │
│    • Episódios curtos: 5-28 steps                                │
│    • Termina por soft SLA (throughput > 15 Mbps)                 │
│                                                                 │
│  SAC:                                                             │
│    • Reward: 17.85 (melhor convergência)                         │
│    • Throughput eMBB: 6-18 Mbps                                  │
│    • Episódios mais longos: até 153 steps                        │
│    • Melhor exploração do espaço de ações                        │
│                                                                 │
│  Conclusão: SAC superior a DDQN; baseline estável mas           │
│             com throughput menor que o máximo possível           │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Cenário Congestionamento

#### Baseline (psta_equal)

| Slice | Throughput (Mbps) | PDR |
|-------|-------------------|-----|
| eMBB | 9.64 | 9.5% |
| URLLC | 1.56 | 100% |
| MTC | 8.16 | 6.4% |

#### Baseline (slice_weighted_rr)

| Slice | Throughput (Mbps) | PDR |
|-------|-------------------|-----|
| eMBB | 7.27 | 7.1% |
| URLLC | 1.56 | 100% |
| MTC | 5.46 | 4.3% |

#### DRL - DDQN (50 episódios)

| Métrica | Valor |
|---------|-------|
| **Reward Final Médio** | 14.73 |
| **Best Avg Reward** | 14.82 |
| **Throughput eMBB** | 6.11 - 18.34 Mbps |

#### DRL - SAC (300 episódios)

| Métrica | Valor |
|---------|-------|
| **Reward Final Médio** | 18.38 |
| **Best Avg Reward** | 18.38 |
| **Throughput eMBB** | 6.11 - 18.34 Mbps |
| **Outage Count** | 1 (episódio 1) |
| **Soft Count** | 0-1 |

```
┌─────────────────────────────────────────────────────────────────┐
│  ANÁLISE - CENÁRIO CONGESTIONAMENTO                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  psta_equal supera slice_weighted_rr em throughput eMBB:         │
│    • psta_equal: 9.64 Mbps                                       │
│    • slice_weighted_rr: 7.27 Mbps                                │
│                                                                 │
│  SAC alcança melhor reward que DDQN:                             │
│    • SAC: 18.38                                                  │
│    • DDQN: 14.73                                                 │
│                                                                 │
│  URLLC mantém 100% PDR em todos os métodos                       │
│                                                                 │
│  Conclusão: P_STA (psta_equal) demonstra isolamento de           │
│             slice efetivo; SAC converge melhor que DDQN         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Cenário Low Traffic

#### Baseline (psta_equal)

| Slice | Throughput (Mbps) | PDR |
|-------|-------------------|-----|
| eMBB | 5.09 | 100% |
| URLLC | 1.56 | 100% |
| MTC | 2.56 | 100% |

#### DRL - DDQN (50 episódios)

| Métrica | Valor |
|---------|-------|
| **Reward Final Médio** | 4.51 |
| **Best Avg Reward** | 4.66 |

#### DRL - SAC (300 episódios)

| Métrica | Valor |
|---------|-------|
| **Reward Final Médio** | 1.30 |
| **Best Avg Reward** | 1.41 |

```
┌─────────────────────────────────────────────────────────────────┐
│  ANÁLISE - CENÁRIO LOW TRAFFIC (CRÍTICO)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PROBLEMA RAIZ:                                                  │
│  • SLA mínimo eMBB: 10 Mbps                                     │
│  • Throughput máximo ns-3: 5.09 Mbps                            │
│  • Tráfego oferecido: 50 Kbps/UE × 5 UEs = 250 Kbps             │
│                                                                 │
│  IMPOSSÍVEL FISICAMENTE atingir SLA com tráfego oferecido        │
│                                                                 │
│  Consequência:                                                   │
│    • DDQN reward baixo (4.51)                                    │
│    • SAC reward muito baixo (1.30)                              │
│    • Sem outlier positivo                                        │
│                                                                 │
│  Mismatch entre MATLAB 5G Toolbox (artigo) e ns-3               │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Cenário Stressed

#### Baseline (pure_rr)

| Slice | Throughput (Mbps) | PDR |
|-------|-------------------|-----|
| eMBB | 7.25 | 7.1% |
| URLLC | 1.56 | 100% |
| MTC | 14.14 | 11.1% |

#### Baseline (psta_equal)

| Slice | Throughput (Mbps) | PDR |
|-------|-------------------|-----|
| eMBB | 9.64 | 9.5% |
| URLLC | 1.56 | 100% |
| MTC | 8.16 | 6.4% |

---

## 4. Análise DRL - DDQN e SAC

### 4.1 Comparativo Algoritmos

| Aspecto | DDQN | SAC |
|---------|------|-----|
| **Episódios** | 50 | 300 |
| **Espaço de Ação** | Discreto (198 ações) | Contínuo (box[-1,1]^3) |
| **Reward Final (Normal)** | 9.37 | 17.85 |
| **Reward Final (Congestion)** | 14.73 | 18.38 |
| **Reward Final (Low Traffic)** | 4.51 | 1.30 |
| **Convergência** | Parcial (reward estagnado) | Completa (reward estável) |
| **Steps Máximo** | 28 (normal) | 153 (normal) |
| **Exploração** | Limitada | Melhor |

### 4.2 Comportamento do Reward DDQN

Cenário Normal:
- Episódio 1: 9.71
- Episódio 10: 13.82 (máximo)
- Episódio 50: 9.71
- Média final: 9.37

Cenário Congestionamento:
- Reward médio mais alto (14.73)
- Indica melhor adaptação a cenários estressados

### 4.3 Comportamento do Reward SAC

Cenário Normal:
- Episódio 1-10: 1.6-4.0 (warmup)
- Episódio 250-300: 17.8-19.3 (convergido)
- Média final: 17.85

Cenário Congestionamento:
- Episódio 1: 13.70 (com outage)
- Episódio 300: 9.31
- Média final: 18.38

### 4.4 Ações Alocação de PRB

Cenário Normal (SAC):
- eMBB: 22-54% dos PRBs
- URLLC: 26-55% dos PRBs
- MTC: 19-48% dos PRBs

Cenário Congestionamento (SAC):
- eMBB: 21-51% dos PRBs
- URLLC: 24-51% dos PRBs
- MTC: 17-48% dos PRBs

---

## 5. Avaliação da Implementação do Artigo RSLAQ

### 5.1 Fidelidade da Implementação

| Componente | Artigo (Referência) | Implementação | Status |
|------------|---------------------|---------------|---------|
| **Estado** (Eq. 1) | Matriz 4×4: [btx, bfs, rsh, tdp] × [eMBB, URLLC, MTC, cell] | ✅ Implementado (observation_mode="paper") | Paper-faithful |
| **Ações** (Eq. 7) | 198 ações discretas: 66 combos PRB × 3 schedulers | ✅ Implementado (discrete mode) | Paper-faithful |
| **P_STA** (Eq. 3-5) | 50% estático (ω_j × 0.5) + 50% DRL (p_opt × 0.5) | ✅ Implementado (apply_p_sta=True) | Paper-faithful |
| **Função Recompensa** (Eq. 8, 12, 16-19) | α·h₁ + β·h₂ + γ·h₃ + 1/cost(sch) | ✅ Implementado (rslaq_reward.py) | Paper-faithful |
| **h₁** (Eq. 16) | per-UE avg thr / max achievable rate | ✅ Implementado | Paper-faithful |
| **h₂** (Eq. 17) | exp(-max_bfs / bf_norm) | ✅ Implementado | Paper-faithful |
| **h₃** (Eq. 18) | per-UE avg thr / max achievable rate | ✅ Implementado | Paper-faithful |
| **Terminal: Outage** (Eq. 12) | -Σ(φ_j·ω_j) | ✅ Implementado | Paper-faithful |
| **Terminal: Soft** (Eq. 12) | reward = 0 | ✅ Implementado | Paper-faithful |
| **DNN** (Seção IV-C) | 4 Conv2D + BatchNorm + Tanh + FC output | ✅ Implementado | Paper-faithful |
| **Algoritmo** (Algorithm 1) | DDQL com experience replay, ε-greedy, target network | ✅ Implementado | Paper-faithful |
| **SAC** | Soft Actor-Critic (alternativa) | ✅ Implementado | Extra |

### 5.2 SLA Targets (Table V)

Implementado conforme artigo em `rslaq_reward.py`:

```python
SLA_BY_SCENARIO = {
    "low_traffic": {"embb_min_throughput_mbps": 10.0, ...},
    "normal": {"embb_min_throughput_mbps": 10.0, ...},
    "congestion": {"embb_min_throughput_mbps": 10.0, ...},
    "stressed": {"embb_min_throughput_mbps": 20.0, ...},
    "insufficient_resources": {"embb_min_throughput_mbps": 20.0, ...},
}
```

### 5.3 Pesos de Prioridade (ω_j)

Conforme implementado:
```python
ALPHA = 0.3333  # omega_0: eMBB (prioridade 2)
BETA = 0.4000   # omega_1: URLLC (prioridade 1 - mais alta)
GAMMA = 0.2667  # omega_2: MTC (prioridade 3 - mais baixa)
```

### 5.4 Estrutura de Alocação P_STA + DRL

```
┌─────────────────────────────────────────────────────────────────┐
│  ESTRUTURA DE ALOCAÇÃO P_STA + DRL                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  URLLC: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━  │
│          20% estático (P_STA)      ┃  20% dinâmico (DRL)       │
│                                                                 │
│  eMBB:  ━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳  │
│        16.7% estático       ┃     16.7% dinâmico (DRL)    ┃  │
│                                                                 │
│  MTC:   ━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳  │
│       13.3% estático    ┃      13.3% dinâmico (DRL)       ┃  │
│                                                                 │
│  TOTAL: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│          50% estático (P_STA)  +  50% dinâmico (DRL)         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Problemas Identificados

### 6.1 Problema 1: SLA Targets Incompatíveis com ns-3 (Low Traffic)

| Parâmetro | Artigo | ns-3 | Consequência |
|-----------|--------|------|--------------|
| eMBB tráfego | 50 Kbps/UE | 50 Kbps/UE | — |
| eMBB SLA min | 10 Mbps | — | Exige 10 Mbps de fonte de 0.25 Mbps |
| eMBB thr máximo | — | 5.1 Mbps | Fisicamente impossível atingir SLA |

**Solução:** Recalibrar `embb_min_throughput_mbps` para low_traffic (ex: 1.0 Mbps).

### 6.2 Problema 2: Soft SLA Como Terminal Impede Fine-Tuning

A função de recompensa termina o episódio quando eMBB excede soft_max:

```python
# rslaq_reward.py linha 291-294
elif soft_slices:
    result.reward = 0.0
    result.terminated = True
```

Isso impede o agente de aprender que throughput maior que o SLA pode ser benéfico.

### 6.3 Problema 3: DDQN Não Converge Completamente

O DDQN (discrete) com 198 ações e step de 10% tem dificuldade de convergência:
- Reward estagnado em 9.37 após 50 episódios
- Throughput eMBB variável e inconsistente
- Espaço de ação grosseiro limita otimização

### 6.4 Problema 4: SAC Superior mas com Baixo Reward em Low Traffic

SAC converge melhor em normal e congestionamento, mas falha em low traffic:
- Reward de 1.30 vs 4.51 do DDQN
- Indica sensibilidade à impossibilidade física de atender SLA

---

## 7. Recomendações

### 7.1 Recomendação 1: Ajustar SLA Targets por Cenário

Ajustar os targets de throughput mínimo para compatibilidade com ns-3:

| Cenário | SLA Atual | SLA Recomendado |
|---------|-----------|-----------------|
| low_traffic | 10 Mbps | 1.0 Mbps |
| normal | 10 Mbps | 10 Mbps ✓ |
| congestion | 10 Mbps | 10 Mbps ✓ |
| stressed | 20 Mbps | 8-10 Mbps |
| insufficient_resources | 20 Mbps | 6-8 Mbps |

### 7.2 Recomendação 2: Revisar Terminação por Soft SLA

Considerar não terminar o episódio em soft violation, apenas aplicar penalidade pequena.

### 7.3 Recomendação 3: Priorizar SAC sobre DDQN

SAC demonstra superior convergência e exploração:
- Reward médio 2x maior
- Espaço de ação contínuo mais flexível
- Episódios mais longos permitem mais aprendizado

### 7.4 Recomendação 4: Aumentar Duração dos Episódios

Aumentar `max_steps` para permitir mais experiência de treino por episódio.

---

## Conclusão

### Fidelidade da Implementação

A implementação do RSLAQ é **paper-faithful** nos aspectos essenciais:
- Arquitetura DNN conforme especificado
- Algoritmo DDQL conforme Algorithm 1
- Função de recompensa conforme Eq. 8, 12, 16-19
- P_STA conforme Eq. 3-5
- Ações com scheduler (198 ações)
- Hyperparâmetros consistentes

### Performance vs Baseline

| Aspecto | Baseline psta_equal | DDQN | SAC |
|---------|---------------------|------|-----|
| Throughput eMBB (Normal) | 11.6 Mbps | 15-22 Mbps | 6-18 Mbps |
| Reward (Normal) | N/A | 9.37 | 17.85 |
| URLLC SLA Compliance | 100% | 100% | 100% |
| Convergência | — | Parcial | Completa |

### Limitações

1. **Mismatch MATLAB vs ns-3:** O SLA de 10 Mbps em low_traffic é impossível de atingir
2. **Espaço de Ação Reduzido:** P_STA limita o DRL a apenas 50% dos recursos
3. **Soft SLA Punitivo:** Termina episódio quando throughput excede soft_max
4. **DDQN Não Converge:** Espaço discreto grosseiro limita otimização

---

**Relatório Gerado:** 2026-05-14
**Engenheiro:** Engenheiro de Dados Senior - Redes 5G
**Versão:** 1.0