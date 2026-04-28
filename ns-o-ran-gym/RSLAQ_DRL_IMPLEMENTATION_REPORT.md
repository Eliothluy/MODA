# RSLAQ DRL Implementation Report

**Status:** DRL resource-only inspirada no RSLAQ, com estado/reward parcialmente alinhados ao artigo e preparada para futura extensão com métricas reais de buffer/drop e seleção RR/PF/BCQI.

---

## 1. Resumo Executivo

Este relatório documenta a implementação da camada DRL no ambiente `ns-o-ran-gym`, alinhada ao artigo RSLAQ (Robust SLA-driven 6G O-RAN QoS xApp using deep reinforcement learning).

Foram corrigidos problemas críticos de deslocamento de `sliceId`, refatorado o ambiente para suportar modos de ação contínua (SAC) e discreta (DDQN), implementado o espaço de observação `4x4` do artigo, criada uma função de recompensa SLA-aware configurável por cenário, e ajustados os scripts de treino para horizonte de episódio coerente com a simulação ns-3.

---

## 2. Arquitetura Final

```
ns-o-ran-gym/
├── src/environments/
│   ├── rslaq_env.py              # Ambiente Gymnasium (modos contínuo/discreto, observation paper/debug)
│   ├── rslaq_slice_ids.py        # Padronização 0-based de slice IDs
│   ├── rslaq_action_spaces.py    # Conversão contínua/discreta -> PRB %
│   ├── rslaq_kpis.py             # Parser de KPMs e construtor de estado 4x4
│   └── rslaq_reward.py           # Reward SLA-aware por cenário
├── examples/
│   ├── rslaq_train_sac.py        # Treino SAC com logging CSV
│   ├── rslaq_train_ddqn.py       # Treino DDQN com action table e epsilon-greedy
│   └── rslaq_eval_policy.py      # Avaliação de política + baselines fixos
└── tests/
    ├── test_rslaq_slice_ids.py
    ├── test_rslaq_action_spaces.py
    ├── test_rslaq_kpis.py
    └── test_rslaq_reward.py
```

### Fluxo de Dados

1. **ns-3** escreve `rslaq-kpms.txt` (CSV com `sliceId=0,1,2`).
2. **`rslaq_kpis.parse_kpm_file`** lê e agrega métricas por slice.
3. **`rslaq_kpis.build_observation`** monta matriz `(4,4)`:
   - rows: `btx`, `bfs`, `rsh`, `tdp`
   - cols: `eMBB`, `URLLC`, `MTC`, `cell`
4. **Agente** (SAC ou DDQN) recebe `obs` e envia ação.
5. **`rslaq_action_spaces`** converte ação bruta em PRB percentages (`dedicatedPRB`).
6. **ns-3** lê `rslaq_actions_for_ns3.csv` e aplica alocação.
7. **`rslaq_reward.compute_rslaq_reward`** calcula recompensa baseada em SLAs do cenário.

---

## 3. Arquivos Alterados / Criados

### Novos módulos auxiliares
- `src/environments/rslaq_slice_ids.py`
- `src/environments/rslaq_action_spaces.py`
- `src/environments/rslaq_kpis.py`
- `src/environments/rslaq_reward.py`

### Refatorados
- `src/environments/rslaq_env.py`
  - Suporte a `action_mode="continuous" | "discrete"`
  - Suporte a `observation_mode="paper" | "debug"`
  - Cálculo automático de `max_steps` a partir de `simTime`, `appStart`, `periodMs`
  - Slice IDs 0-based (`0=eMBB, 1=URLLC, 2=MTC`)
  - `info` rico com KPIs por slice, flags de outage/soft violation, ação final

### Scripts de treino
- `examples/rslaq_train_sac.py` — reescrito do zero
- `examples/rslaq_train_ddqn.py` — reescrito do zero

### Novos scripts
- `examples/rslaq_eval_policy.py` — avaliação com baselines

### Testes
- `tests/test_rslaq_slice_ids.py`
- `tests/test_rslaq_action_spaces.py`
- `tests/test_rslaq_kpis.py`
- `tests/test_rslaq_reward.py`

---

## 4. Como Rodar

### Instalar pacote (opcional, para importações)
```bash
cd ns-o-ran-gym
pip3 install -e .
```

### Treinar SAC
```bash
python3 examples/rslaq_train_sac.py \
    --scenario normal \
    --episodes 10 \
    --simTime 4.0 \
    --periodMs 10 \
    --observation_mode paper \
    --action_mode continuous \
    --output results/sac_normal
```

Para treinamento generalista (cenário aleatório por episódio):
```bash
python3 examples/rslaq_train_sac.py \
    --scenario random \
    --scenarios normal,congestion,stressed \
    --episodes 50 \
    --output results/sac_generalist
```

### Treinar DDQN
```bash
python3 examples/rslaq_train_ddqn.py \
    --scenario normal \
    --episodes 10 \
    --simTime 4.0 \
    --periodMs 10 \
    --observation_mode paper \
    --action_mode discrete \
    --output results/ddqn_normal
```

### Avaliar Política
```bash
python3 examples/rslaq_eval_policy.py \
    --algo sac \
    --checkpoint results/sac_normal/sac_best.pt \
    --scenario normal \
    --episodes 5 \
    --output results/eval
```

---

## 5. O que Reproduz o Artigo

| Componente | Status | Notas |
|------------|--------|-------|
| Estado `s ∈ R^{4x4}` | Implementado | `observation_mode="paper"` retorna `(4,4)` |
| Ação contínua SAC | Implementado | `Box(-1,1,(3,))` com softmax + P_STA |
| Ação discreta DDQN | Implementado | Tabela com 66 ações (resource-only) |
| P_STA decomposition | Implementado | `p_final = 0.5 * weights + 0.5 * p_opt` |
| Reward SLA-aware | Implementado | Configurável por cenário, com outage/soft flags |
| Seleção de cenário | Implementado | Modo fixo e modo `random` por episódio |

---

## 6. O que Ainda é Aproximação / Proxy

| Componente | Status | Notas |
|------------|--------|-------|
| `bfs` (buffer status) | Proxy | Usa `plr` (packet loss ratio) como proxy de backlog/congestionamento |
| `tdp` (dropped bytes) | Proxy | Usa `dLostPackets` como proxy de pacotes perdidos |
| Delay URLLC | Proxy | Não há métrica direta de delay no KPM; derivado indiretamente |
| Scheduler RR/PF/BCQI | Não integrado | C++ do ns-3 ainda não lê coluna `algorithm`; infraestrutura Python pronta (`include_scheduler`) |

**TODOs principais:**
- `TODO(bfs-real)`: Adicionar `bufferSize`/`bufferStatus` real no `rslaq-kpms.txt` do ns-3.
- `TODO(tdp-real)`: Adicionar métrica real de dropped/transmitted-dropped bytes no ns-3.
- `TODO(scheduler-cpp)`: Atualizar parser C++ de `rslaq_actions_for_ns3.csv` para aceitar coluna `algorithm`.

---

## 7. Limitações Conhecidas

1. **Scheduler-aware desativado**: O parser C++ de ações (`rslaq-sim.cc`) não lê a coluna `algorithm`. A infraestrutura Python (`include_scheduler=True`) está pronta, mas ativá-la agora quebraria a compatibilidade.
2. **Proxies no estado**: `bfs` e `tdp` dependem de métricas indiretas. Isso afeta a fidelidade da reward em cenários extremos.
3. **BatchNorm removido**: O DDQN não usa BatchNorm para evitar instabilidade com batch pequeno. Redes mais profundas podem precisar de LayerNorm/GroupNorm.
4. **Semente reprodutível**: `set_seed` cobre Python, NumPy e PyTorch, mas a reprodutibilidade completa depende do ns-3 (que usa seu próprio RNG).
5. **Single gNB**: A topologia ns-3 atual suporta apenas 1 gNB, conforme documentado.

---

## 8. Próximos Passos

1. **Adicionar métricas reais no ns-3**:
   - Exportar `bufferSize` no `rslaq-kpms.txt`.
   - Exportar `droppedBytes` ou similar.
2. **Integrar scheduler-aware no C++**:
   - Modificar parser de `rslaq_actions_for_ns3.csv` para ler `algorithm`.
   - Mapear `algorithm` para `RR=0, PF=1, BCQI=2` no `RslaqMacScheduler`.
3. **Aumentar cobertura de testes**:
   - Testes de integração com mock do ns-3 (sem executar simulação completa).
   - Testes dos scripts de treino com `max_steps=2`.
4. **Hiperparâmetros e tuning**:
   - Realizar grid-search sobre `lr`, `gamma`, `alpha` (SAC), `epsilon_decay` (DDQN).
5. **Suporte a multi-cell**:
   - Adaptar mapeamento RNTI/slice para múltiplas células.

---

## 9. Comandos Testados

```bash
# Testes unitários
cd ns-o-ran-gym
python3 tests/test_rslaq_slice_ids.py
python3 tests/test_rslaq_action_spaces.py
python3 tests/test_rslaq_kpis.py
python3 tests/test_rslaq_reward.py
```

Todos os testes passam com sucesso.

---

## 10. Checklist de Critérios de Aceite

- [x] `sliceId` padronizado como 0/1/2 no Python.
- [x] `RslaqEnv` suporta `action_mode="continuous"` e `"discrete"`.
- [x] `RslaqEnv` suporta `observation_mode="paper"` com shape `(4,4)`.
- [x] SAC envia ação contínua sem conversão duplicada.
- [x] DDQN envia índice discreto, não matriz.
- [x] Reward SLA-aware isolada em módulo próprio.
- [x] Reward usa configuração por cenário.
- [x] `max_steps` calculado corretamente a partir de `simTime`, `appStart` e `periodMs`.
- [x] Ambiente retorna `info` rico com KPIs, ação final e flags de SLA.
- [x] Scripts SAC e DDQN configuráveis por CLI e salvam CSV/logs.
- [x] Resultados salvos com run_id/scenario/seed.
- [x] Relatório final explica claramente o que está implementado e o que ainda é aproximação.
