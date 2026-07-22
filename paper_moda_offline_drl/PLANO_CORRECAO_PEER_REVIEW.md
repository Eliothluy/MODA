# Plano de Correção — Peer Review MODA (Major Revision)

**Artigo:** "MODA: Transforming Offline Metaheuristic Optimization into Online
Resource Allocation Policies for Network Slicing"
**Veredito do revisor:** Major Revision (média 5.8/10)
**Data do plano:** 2026-07-19

Estado de cada problema: ✅ **resolvido** (número/texto pronto neste documento) ·
📦 **dados prontos** (só falta escrever no paper) · 🧪 **experimento novo** ·
⚖️ **decisão de escopo**.

Restrição operacional: a máquina está ocupada ~2 dias com o piloto v2 da linha
de metaheurísticas. Tarefas **CPU-only** (retreinos, ablações, texto) podem ser
feitas agora; tarefas que exigem **ns-3** entram na fila pós-piloto.

---

## R1. Custo computacional nunca quantificado (Exigência 3 — a mais grave) ✅

**Medido em 2026-07-19** (CPU, checkpoints reais em `models/`):

| Política | Parâmetros | Tamanho | Latência média | Latência p99 |
|---|---:|---:|---:|---:|
| MODA-Q (ddqn) | 26.946 | 114 KB | 0.075 ms | 0.132 ms |
| MODA-BC (sac) | 18.819 | 81 KB | 0.062 ms | 0.132 ms |
| MODA-RWR (ppo) | 18.822 | 81 KB | 0.101 ms | 0.155 ms |

*(1.000 inferências após 50 de warm-up; `predict_weights` fim-a-fim com
normalização de estado.)*

**Custo da alternativa online (dados da campanha/auditoria):**
- 1 avaliação ns-3 (simTime=5s): **47–160 s** de wall-clock;
- 1 busca metaheurística por (cenário, seed): 72 avaliações ≈ **1–3.2 h**;
- campanha offline completa (3.600 avaliações): ≈ **47–160 h de CPU**, custo
  único e amortizado sobre todas as implantações da política.

**Conclusão quantitativa para o paper:** a inferência MODA é ~**7 ordens de
grandeza** mais rápida que uma única avaliação de candidato, e cabe com folga
no loop do Near-RT RIC (10 ms–1 s); a otimização iterativa não cabe (uma busca
excede o loop em ~4 ordens de grandeza).

**Ação:** inserir tabela + parágrafo na Seção de Resultados. Script de
reprodução do benchmark: incluir em `examples/` (`benchmark_moda_inference.py`
— trivial, extraído do comando usado; ~20 linhas).

---

## R2. A metaheurística não é descrita (Exigência 1) 📦

Tudo existe e é rastreável; falta só escrever. Especificação completa a inserir
na Seção III:

- **Métodos da campanha:** GA, PSO, SA e híbrida (não uma só — o dataset union
  das 4 buscas).
- **Hiperparâmetros:** `iterations=12`, `population=6`; orçamento 72 evals
  (GA/PSO/SA; SA equalizado ao produto iterations×population) e 84 (híbrida:
  +1 refinamento local SA por iteração — declarar os +17%). PSO: inércia 0.55,
  c1=c2=1.30; GA: elitismo + crossover blend + mutação gaussiana σ=0.12;
  SA: temperatura decrescente, perturbação gaussiana. População inicial
  semeada com priors estruturados (uniforme, [0.3333,0.40,0.2667], etc. —
  lista em `seed_weight_candidates`, `run_rslaq_metaheuristics.py`).
- **RNG:** `random.Random(2026)` consumido sequencialmente GA→PSO→SA→híbrida
  por par (cenário, seed).
- **Dataset D:** 3.722 tuplas = 3.591 avaliações metaheurísticas + 131 runs de
  heurísticas adaptativas (pesos dinâmicos entram como média temporal
  renormalizada de `configured_weight`, tag `weight_provenance="time_averaged"`;
  schedulers puros RR/PF/BCQI são EXCLUÍDOS — sem semântica de peso).
  Partição 80/20 por grupos (scenario, seed).
- **Cenários:** 4 (low_traffic 57, normal 73, stressed 128, congestion 245
  Mbps ofertados), 3 seeds, simTime=5s.

**Ação:** escrever a subseção "Optimization campaign" (~2 parágrafos + tabela
de hiperparâmetros). Fonte: `CLAUDE.md`, `run_rslaq_metaheuristics.py`.

---

## R3. Composite score não definido (Exigência 2) 📦

Fórmula exata (v1, a usada no dataset do MODA — `nsoran/scoring.py`):

```
F(w) = 100·(0.35·mean_SLA + 0.20·min_SLA + 0.20·mean_offered
            + 0.15·mean_PDR + 0.10·mean_util)
       − 25·clamp((delay_URLLC_mean − 10)/20, 0, 1)          [penalidade URLLC]
       − 40·[max(0, 1 − SLA_MTC) + 0.5·1{thr_MTC ≈ 0}]      [starvation MTC]
       − 100·0.05·clamp(buffer_eMBB / 5·10⁶, 0, 1)           [buffer eMBB]
```

Todos os termos normalizados a [0,1] antes da combinação; escala final ≈
[−100, 100] na prática (crash → −10⁶ sentinela, excluído do dataset).

**Ação:** inserir como equação numerada + tabela de pesos. **Honestidade
obrigatória:** citar que uma auditoria posterior identificou limitações desta
função (recompensa starvation em casos extremos — caso documentado
sa_eval_0021) e que ela é usada aqui como *fonte de supervisão histórica*, com
as implicações discutidas na seção de limitações. Isso converte uma fraqueza
em transparência — e conecta com R6.

---

## R4. Validação estatística insuficiente (n=3) (Exigência 6) 🧪 pós-piloto

**Experimento:** estender a avaliação em malha fechada para **seeds 1–10**.
- Comando: `eval_offline_rl_closedloop.py --seeds 1 2 3 4 5 6 7 8 9 10`
  (o script já aceita `--seeds`; cache pula as seeds 1–3 já feitas).
- Volume: 6 métodos × 4 cenários × 7 seeds novas ≈ **168 runs ns-3 a 5s**
  ≈ 6–12 h com 6 jobs. **Fila: depois do piloto v2.**
- Estatística: reutilizar o padrão de `analyze_v2_stats.py` (Friedman +
  Wilcoxon pareado + effect size + IC bootstrap) sobre score por seed.
- **Fallback** (se não houver tempo de máquina): remover alegações de ranking
  entre variantes MODA e reescrever como análise descritiva — o revisor
  aceita explicitamente essa alternativa.

---

## R5. Circularidade / one-hot / generalização (Exigência 5) 🧪 duas partes

**(a) Remover one-hot — CPU-only, pode rodar AGORA:**
- Retreinar as 3 variantes com vetor de estado só de features observáveis
  (nº UEs por slice, carga ofertada por slice, tamanho de pacote) removendo
  `is_low_traffic/normal/congestion/stressed` de `STATE_COLS`.
- Custo: minutos de CPU (`train_offline_rl.py`, 300 épocas, rede 2×128).
- Reportar delta de desempenho com/sem one-hot (proxy + malha fechada).

**(b) Teste de generalização real — ns-3, fila pós-piloto:**
- **Cenário held-out já existe:** `insufficient_resources` (295 Mbps) NUNCA
  entrou no treino — avaliação zero-shot direta das políticas (a) nele.
- **Carga intermediária:** criar cenário interpolado (~100 Mbps, entre normal
  73 e stressed 128) via overrides de CLI do ns-3 (`--numUe*`, taxas por
  slice) sem tocar no código; avaliar zero-shot.
- Volume: 3 políticas × 2 cenários × 3–10 seeds ≈ 18–60 runs.

Este é o experimento que muda o patamar do paper (in-distribution →
out-of-distribution).

---

## R6. Baseline "Best meta." ambígua + hipótese de overfitting à seed (Exigência 4) ✅

**Clarificação:** é a melhor alocação **por (cenário, seed)** — não global.

**A hipótese do revisor está CONFIRMADA com dados que já temos**
(`models/evaluation_closedloop.csv`, re-execuções no mesmo ambiente):
- O ótimo de congestion `w=[0.816, 0.180, 0.004]` (otimizado na seed 2) ao ser
  re-executado nas 3 seeds: **61.8 ± 32.9** (colapsa numa seed: mín 24.4),
  enquanto MODA-BC dá **82.6 ± 5.4** nas mesmas seeds.
- Mecanismo físico documentado (`closedloop_radio_efficiency_*.csv`): o ótimo
  estrangula o MTC (21% dos RBGs → satisfação 31%, delay 1289 ms), típico de
  sobreajuste ao realization de ruído da seed de busca.
- Explicação para "a destilação supera a fonte de supervisão": a política
  aprende a REGIÃO de bons pesos (média sobre candidatos/vizinhanças), não o
  ponto extremo de uma seed — regularização implícita da regressão. Com a
  fonte re-avaliada *fora* da sua seed de origem, a política generaliza melhor
  por construção.

**Ação:** parágrafo de definição + subseção curta "Why distillation can beat
its own supervision" com esses números. Zero experimento novo.

---

## R7. Falta baseline RL online (Exigência 8) — DECIDIDO: incluir RSLAQ DDQN online

**Decisão do usuário (2026-07-20):** incluir o **RSLAQ DDQN online real** como
baseline (não apenas "RSLAQ fixed"), rodado APÓS o piloto de metaheurísticas
concluir (os dois são ns-3 CPU-bound e não coexistem).

**Auditoria de fidelidade ao paper (`_RSLAQ-...pdf`, feita 2026-07-19/20):** a
implementação do repositório é fiel — verificado item a item:
- Estado 4×4 `[btx,bfs,rsh,tdp]×[m1,m2,m3,cell]` (Eq. 1) → `rslaq_kpis.build_observation(mode="paper")`
- 198 ações = 66 pesos × {RR,PF,BCQI} (Eq. 2,7) → `build_discrete_action_table(step=0.1, include_scheduler=True)`
- P_STA semi-dinâmico 50/50 (Eq. 3-5), ω=[0.3333,0.4000,0.2667]
- Recompensa Eqs. 8/9/11/12/16-18 → `rslaq_reward.py` (modo `paper`); targets Tabela V → `SLA_TARGETS_BY_SCENARIO` (5 cenários idênticos aos nossos)
- DDQN 4×Conv2D+BN+Tanh+FC (Seção IV-C), γ=0.80, ε_decay=0.998, ε_min=0.05, target_update=200, 35×100=3500 steps → `rslaq_train_ddqn.py`
- Cenários/TDD/UEs idênticos (Tabela IV/V): TDD `D|D|8D|4GB|4U|U|U`, 20 UEs (5/5/10), μ=1.

**Divergência a corrigir para fidelidade máxima:** buffer/batch do trainer
(`L=128, btsz=32`) < Hyp-set3 do paper (`L=500, btsz=350`). Rodar com
`--buffer_size 500 --batch_size 350` (checar estabilidade; se episódios ns-3
forem curtos demais para encher L=500, documentar o desvio).

**Custo medido (smokes 2026-07-20, sob contenção do piloto):**
- low_traffic: ~0.75 s/step → ~45 min/seed (3500 steps)
- congestion: ~15.8 s/step (contended) → ~15h/seed contended, ~5h/seed limpo
- **Full 5 cenários × 10 seeds ≈ 1–2 semanas** de máquina dedicada.

**Plano de execução (pós-piloto):** definir escopo no momento (recomendo
começar por 3 cenários × 3–5 seeds para o RSLAQ online, declarando n do baseline
como limitação, e expandir se houver tempo). Avaliar as políticas RSLAQ
resultantes pelo MESMO caminho de score/KPI que o MODA (extrair pesos via
`ingest_online_rslaq.py` → re-avaliar em malha fechada), para comparação justa.
Ver medições em AGENTS.md §14.7.

---

## R8. Hiperparâmetros das redes omitidos + ablação (Exigência 7) 📦 + 🧪 CPU-only

**Reportar (tudo já conhecido, `train_offline_rl.py`):**
- Arquitetura: MLP 2×128, ReLU; cabeças — Q: |A|=66 saídas; BC/RWR: 3 +
  softmax (simplex por construção).
- Otimizador Adam, lr=1e-3, 300 épocas, **gradiente full-batch** (declarar
  honestamente — a constante BATCH_SIZE não é usada como minibatch), seed 42.
- Split 80/20 por grupos (scenario, seed). Dataset N=3.722.
- δ=0.1 (66 ações no simplex), τ=0.1 (RWR), elite = quantil 0.8 por cenário.

**Ablação mínima (CPU, minutos–horas, pode rodar AGORA):**
- δ ∈ {0.05, 0.10, 0.20} → |A| ∈ {231, 66, 21};
- τ ∈ {0.05, 0.1, 0.5, 1.0};
- quantil de elite ∈ {0.7, 0.8, 0.9}.
- Avaliação por proxy (dataset) para a grade completa + malha fechada (ns-3,
  pós-piloto) só para o melhor/pior de cada eixo.

---

## R9. Simulação de 5 s (justificar ou sensibilidade) 🧪 pós-piloto

- **Sensibilidade:** re-executar as alocações preditas dos 3 modelos ×
  4 cenários × 3 seeds a `simTime=15s` (36 runs; o closed-loop já parametriza
  `SIM_TIME`) e comparar ordenação/escala dos scores 5s vs 15s.
- **Sinergia:** a linha v2 das metaheurísticas já migrou para 15s — citar como
  validação cruzada.
- **Justificativa textual:** 5s foi o protocolo da campanha-fonte (o dataset
  herda essa duração); a sensibilidade mostra se a ordenação é estável.

---

## R10. Cenário único / generalização excessiva na conclusão ✅ texto

- Reescrever a conclusão limitando o claim ao setup ("single-cell downlink
  scenarios under the evaluated traffic profiles").
- Mover multi-célula/mobilidade/E2 real para future work explícito.
- Já temos a frase de limitação da interface xApp — mantê-la.

---

## Cronograma proposto

| Fase | Itens | Depende de ns-3? | Quando |
|---|---|---|---|
| A (agora) | R1 ✅, R2, R3, R6, R7-texto, R8-reporte, R10 | não | imediato |
| B (agora, CPU) | R5a (retreino sem one-hot), R8-ablação | não | paralelo ao piloto |
| C (pós-piloto) | R4 (10 seeds), R5b (held-out + interpolação), R9 | **sim** | após ~2 dias |
| D (decisão) | R7-opção 2 (RSLAQ online) | sim (dias) | versão periódico |

Com A+B+C atendidos, cobrem-se as Exigências 1–7 integralmente e a 8 por
atenuação — o próprio revisor indica que isso qualifica o trabalho para
GLOBECOM/ICC/NOMS.

## Artefatos/fontes de cada correção

- Benchmark inferência: comando reproduzido em `examples/` (a criar:
  `benchmark_moda_inference.py`).
- Fórmula do score: `ns-o-ran-gym/src/nsoran/scoring.py` (v1).
- Spec da campanha: `examples/run_rslaq_metaheuristics.py`, `CLAUDE.md`.
- Overfitting do best-meta: `models/evaluation_closedloop.csv`,
  `models/closedloop_radio_efficiency_per_slice.csv`.
- Avaliação 10 seeds: `examples/eval_offline_rl_closedloop.py --seeds 1..10`.
- Estatística: padrão de `examples/analyze_v2_stats.py`.
- Retreino sem one-hot / ablação: `examples/train_offline_rl.py` (+ flag a
  adicionar para o conjunto de features).
