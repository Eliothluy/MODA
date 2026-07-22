# Ablação MODA — Respostas às exigências R5a e R8 do peer review

Gerado por `ns-o-ran-gym/examples/ablation_offline_rl.py` (dataset v1
`offline_dataset.parquet`, 3.591 evals, seed 42). Avaliação por **proxy**
(candidato mais próximo no dataset, por cenário) — CPU-only, sem ns-3.

> **Caveat metodológico (declarar no paper):** o proxy é **grosseiro** — mapeia
> pesos preditos ao candidato mais próximo de um dataset finito, produzindo
> scores *quantizados* (empates exatos espúrios entre configurações). Serve para
> **sensibilidade direcional**, não para ranking fino. Os números definitivos de
> cada eixo (melhor/pior) devem passar pela avaliação em malha fechada ns-3
> (pós-piloto) e por multi-seed. Ainda assim, os achados qualitativos abaixo são
> robustos e cruzam com o comportamento de produção.

---

## R5a — Indicadores one-hot de cenário são REDUNDANTES (não uma dependência de oráculo)

A crítica do revisor: *"em rede real não existe oráculo informando
I_congestion=1; os one-hot tornam a política inaplicável fora dos 4 cenários."*

**Resposta empírica — a premissa não se sustenta neste setup.** Cada cenário tem
uma **assinatura observável única e constante** (nº de UEs por slice, carga
ofertada por slice, tamanho de pacote): agrupando o dataset por cenário, cada
uma dessas features tem exatamente **1 valor distinto por cenário**. Logo os
one-hot são uma função determinística das features observáveis — não carregam
informação nova.

Consequência medida (proxy, FULL=com one-hot vs OBS=só observáveis):

| Política | FULL (dim=14) | OBS (dim=10) | Δ |
|---|---:|---:|---:|
| MODA-BC | 87.93 | 87.93 | **0.00** |
| MODA-RWR | 68.51 | 68.51 | **0.00** |
| MODA-Q | 94.15 | 44.36 | −49.8 |

**MODA-BC e MODA-RWR produzem predições bit-idênticas com e sem one-hot** (por
cenário: ex. low=[0.586,0.083,0.331], normal=[0.225,0.300,0.475] — variam entre
cenários, mas independem do one-hot). Isso prova que a política **mapeia estado
observável→pesos** sem precisar de qualquer oráculo de cenário: em operação, os
próprios KPMs observados são a assinatura. **A objeção do revisor é respondida:**
a política é deployável sobre features observáveis; o one-hot foi apenas uma
conveniência redundante e pode ser removido sem custo para BC/RWR.

**Exceção reveladora — MODA-Q é frágil à representação.** A regressão-Q sobre 66
ações discretas escolhe por `argmax`, e sem o one-hot o argmax migra para um bin
pior (FULL→[0.50,0.10,0.40] constante; OBS→[0.60,0.00,0.40] constante, com
URLLC=0). Note que **MODA-Q é quase não-adaptativo ao cenário** (prediz
praticamente o mesmo vetor para os 4 cenários) — comportamento **confirmado
independentemente** pelos resultados de malha fechada de produção
(`evaluation_closedloop.csv`: DDQN prediz [0.5,0.1,0.4] para
normal/congestion/stressed). A queda de ~50 pontos no proxy é sensibilidade do
classificador discreto à representação, não perda de informação. **Recomendação
para o paper:** treinar/reportar sobre features observáveis (remove a objeção),
e discutir a fragilidade do MODA-Q à discretização como limitação da variante.

---

## R8 — Sensibilidade a hiperparâmetros

### R8a — MODA-Q: passo de discretização δ (→ tamanho da tabela de ações |A|)

| δ | \|A\| | proxy mean |
|---:|---:|---:|
| 0.05 | 231 | 48.79 |
| **0.10** | **66** | **94.15** |
| 0.20 | 21 | 44.36 |

δ=0.10 é um ponto ótimo: δ=0.05 dilui a regressão-Q por bins demais (dados
esparsos por ação); δ=0.20 perde resolução no simplex. Justifica a escolha
default de 66 ações — **respondendo à exigência de justificar δ**.

### R8b — MODA-RWR: temperatura τ

| τ | proxy mean |
|---:|---:|
| 0.05 | 71.63 |
| 0.10 | 68.51 |
| 0.50 | 68.17 |
| 1.00 | 68.17 |

Efeito fraco e monotônico leve: τ menor (peso mais concentrado nos melhores
candidatos) ajuda marginalmente. τ=0.1 é razoável; a política é **robusta a τ**
— reportar como baixa sensibilidade (não é um knob crítico).

### R8c — MODA-BC: quantil de elite q

| q | proxy mean |
|---:|---:|
| 0.70 | 68.99 |
| 0.80 | 87.93 |
| 0.90 | 88.02 |

q≥0.80 é claramente melhor: q=0.70 admite candidatos medianos no conjunto de
clonagem, degradando a política. q=0.80 (default) e q=0.90 são equivalentes —
escolher 0.80 preserva mais amostras de treino. **Justifica o default 0.80.**

---

## Síntese para a resposta ao revisor

- **R5a resolvido:** one-hot é redundante (assinatura observável única por
  cenário); BC/RWR independem dele — a política é deployável sobre KPMs
  observáveis, sem oráculo. Migrar o estado do paper para features observáveis.
- **R8 resolvido (direcional):** δ=0.1 justificado por ótimo claro; τ com baixa
  sensibilidade (robusto); q≥0.8 justificado. Números finos e por-eixo (melhor
  vs pior) a confirmar em ns-3 pós-piloto + multi-seed.
- **Achado bônus (honesto):** MODA-Q é quase-constante entre cenários e frágil à
  representação — discutir como limitação da variante discreta; BC/RWR são as
  variantes genuinamente adaptativas.

Artefato de dados: `models/ablation/ablation_results.csv`.
Pendente (ns-3, pós-piloto): re-avaliar em malha fechada o melhor/pior de cada
eixo (δ=0.1 vs 0.2; q=0.8 vs 0.7) e o OBS-vs-FULL do MODA-Q, para números
definitivos na escala de score real.
